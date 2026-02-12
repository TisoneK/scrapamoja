"""
Cleanup priority configuration for interrupt handling.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from .config import InterruptConfig


class PriorityOrder(Enum):
    """Priority ordering strategies."""
    SEQUENTIAL = "sequential"  # Execute in order of priority
    PARALLEL = "parallel"     # Execute by priority groups in parallel
    DEPENDENCY_BASED = "dependency_based"  # Execute based on dependencies


@dataclass
class PriorityGroup:
    """Represents a group of cleanup tasks with same priority."""
    name: str
    priority: int
    tasks: List[str]
    parallel_execution: bool = False
    timeout: Optional[float] = None


@dataclass
class CleanupPriorityConfig:
    """Configuration for cleanup priorities and ordering."""
    
    # Default priority values
    default_priorities: Dict[str, int] = field(default_factory=lambda: {
        'database': 100,
        'file': 90,
        'network': 80,
        'browser': 70,
        'custom': 60,
        'checkpoint': 50
    })
    
    # Priority groups for parallel execution
    priority_groups: List[PriorityGroup] = field(default_factory=list)
    
    # Ordering strategy
    ordering_strategy: PriorityOrder = PriorityOrder.SEQUENTIAL
    
    # Priority thresholds
    high_priority_threshold: int = 90
    medium_priority_threshold: int = 70
    low_priority_threshold: int = 50
    
    # Execution settings
    enable_parallel_execution: bool = False
    max_parallel_tasks: int = 3
    priority_timeout_multiplier: float = 1.0  # Multiply base timeout by priority factor
    
    def __post_init__(self):
        """Initialize default priority groups."""
        if not self.priority_groups:
            self._create_default_groups()
    
    def _create_default_groups(self):
        """Create default priority groups."""
        self.priority_groups = [
            PriorityGroup(
                name="critical_cleanup",
                priority=100,
                tasks=["database", "file"],
                parallel_execution=False,
                timeout=30.0
            ),
            PriorityGroup(
                name="network_cleanup",
                priority=80,
                tasks=["network", "browser"],
                parallel_execution=True,
                timeout=45.0
            ),
            PriorityGroup(
                name="finalization",
                priority=60,
                tasks=["checkpoint", "custom"],
                parallel_execution=False,
                timeout=60.0
            )
        ]
    
    def get_task_priority(self, task_type: str) -> int:
        """Get priority for a specific task type."""
        return self.default_priorities.get(task_type, 50)
    
    def set_task_priority(self, task_type: str, priority: int):
        """Set priority for a specific task type."""
        self.default_priorities[task_type] = priority
        self.logger.debug(f"Updated priority for {task_type}: {priority}")
    
    def get_priority_group(self, task_type: str) -> Optional[PriorityGroup]:
        """Get priority group for a task type."""
        for group in self.priority_groups:
            if task_type in group.tasks:
                return group
        return None
    
    def get_tasks_by_priority(self, tasks: List[str]) -> List[str]:
        """Sort tasks by priority based on configuration."""
        if self.ordering_strategy == PriorityOrder.SEQUENTIAL:
            return sorted(tasks, key=lambda t: self.get_task_priority(t), reverse=True)
        
        elif self.ordering_strategy == PriorityOrder.PARALLEL:
            return self._get_parallel_task_order(tasks)
        
        elif self.ordering_strategy == PriorityOrder.DEPENDENCY_BASED:
            return self._get_dependency_based_order(tasks)
        
        else:
            return tasks
    
    def _get_parallel_task_order(self, tasks: List[str]) -> List[str]:
        """Get task order for parallel execution."""
        ordered_tasks = []
        remaining_tasks = tasks.copy()
        
        # Process groups in priority order
        sorted_groups = sorted(self.priority_groups, key=lambda g: g.priority, reverse=True)
        
        for group in sorted_groups:
            group_tasks = [t for t in remaining_tasks if t in group.tasks]
            
            if group_tasks:
                if group.parallel_execution:
                    # Add all tasks in this group
                    ordered_tasks.extend(group_tasks)
                else:
                    # Add tasks sequentially within group
                    group_tasks_sorted = sorted(
                        group_tasks, 
                        key=lambda t: self.get_task_priority(t), 
                        reverse=True
                    )
                    ordered_tasks.extend(group_tasks_sorted)
                
                # Remove processed tasks
                for task in group_tasks:
                    remaining_tasks.remove(task)
        
        # Add any remaining tasks
        ordered_tasks.extend(
            sorted(remaining_tasks, key=lambda t: self.get_task_priority(t), reverse=True)
        )
        
        return ordered_tasks
    
    def _get_dependency_based_order(self, tasks: List[str]) -> List[str]:
        """Get task order based on dependencies (placeholder)."""
        # This would be enhanced with actual dependency tracking
        return self.get_tasks_by_priority(tasks)
    
    def get_timeout_for_task(self, task_type: str, base_timeout: float) -> float:
        """Get timeout for a specific task type."""
        priority = self.get_task_priority(task_type)
        
        # Apply priority-based multiplier
        if priority >= self.high_priority_threshold:
            multiplier = 1.2  # Give high priority tasks more time
        elif priority >= self.medium_priority_threshold:
            multiplier = 1.0
        else:
            multiplier = 0.8  # Low priority tasks get less time
        
        adjusted_timeout = base_timeout * multiplier * self.priority_timeout_multiplier
        
        # Check group-specific timeout
        group = self.get_priority_group(task_type)
        if group and group.timeout:
            adjusted_timeout = min(adjusted_timeout, group.timeout)
        
        return adjusted_timeout
    
    def validate_configuration(self) -> List[str]:
        """Validate the priority configuration."""
        errors = []
        
        # Check priority values
        for task_type, priority in self.default_priorities.items():
            if not isinstance(priority, int) or priority < 0 or priority > 100:
                errors.append(f"Invalid priority for {task_type}: {priority}")
        
        # Check thresholds
        if self.high_priority_threshold <= self.medium_priority_threshold:
            errors.append("High priority threshold must be greater than medium threshold")
        
        if self.medium_priority_threshold <= self.low_priority_threshold:
            errors.append("Medium priority threshold must be greater than low threshold")
        
        # Check parallel settings
        if self.enable_parallel_execution and self.max_parallel_tasks < 1:
            errors.append("Max parallel tasks must be at least 1 when parallel execution is enabled")
        
        # Check groups
        task_in_groups = set()
        for group in self.priority_groups:
            if group.priority < 0 or group.priority > 100:
                errors.append(f"Invalid group priority: {group.priority}")
            
            if group.parallel_execution and len(group.tasks) > self.max_parallel_tasks:
                errors.append(f"Group {group.name} exceeds max parallel tasks")
            
            task_in_groups.update(group.tasks)
        
        # Check for duplicate tasks across groups
        all_tasks = set(self.default_priorities.keys())
        ungrouped_tasks = all_tasks - task_in_groups
        if ungrouped_tasks:
            errors.append(f"Tasks not in any group: {ungrouped_tasks}")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'default_priorities': self.default_priorities.copy(),
            'priority_groups': [
                {
                    'name': group.name,
                    'priority': group.priority,
                    'tasks': group.tasks,
                    'parallel_execution': group.parallel_execution,
                    'timeout': group.timeout
                }
                for group in self.priority_groups
            ],
            'ordering_strategy': self.ordering_strategy.value,
            'high_priority_threshold': self.high_priority_threshold,
            'medium_priority_threshold': self.medium_priority_threshold,
            'low_priority_threshold': self.low_priority_threshold,
            'enable_parallel_execution': self.enable_parallel_execution,
            'max_parallel_tasks': self.max_parallel_tasks,
            'priority_timeout_multiplier': self.priority_timeout_multiplier
        }


class CleanupPriorityManager:
    """Manages cleanup priorities and ordering."""
    
    def __init__(self, config: InterruptConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize priority configuration
        self.priority_config = CleanupPriorityConfig()
        
        # Load configuration from config if available
        self._load_from_config()
        
        # Validate configuration
        self._validate_and_fix()
    
    def _load_from_config(self):
        """Load priority configuration from InterruptConfig."""
        if hasattr(self.config, 'cleanup_priorities'):
            self.priority_config.default_priorities.update(
                self.config.cleanup_priorities
            )
        
        # Load other settings from config
        if hasattr(self.config, 'enable_parallel_cleanup'):
            self.priority_config.enable_parallel_execution = (
                self.config.enable_parallel_cleanup
            )
        
        if hasattr(self.config, 'max_parallel_cleanup_tasks'):
            self.priority_config.max_parallel_tasks = (
                self.config.max_parallel_cleanup_tasks
            )
    
    def _validate_and_fix(self):
        """Validate and fix configuration issues."""
        errors = self.priority_config.validate_configuration()
        
        if errors:
            self.logger.warning(f"Priority configuration errors: {errors}")
            # Apply fixes
            self._apply_fixes(errors)
        
        # Re-validate after fixes
        remaining_errors = self.priority_config.validate_configuration()
        if remaining_errors:
            self.logger.error(f"Unresolved configuration errors: {remaining_errors}")
    
    def _apply_fixes(self, errors: List[str]):
        """Apply automatic fixes for configuration errors."""
        for error in errors:
            if "Invalid priority" in error:
                # Fix invalid priority values
                self._fix_invalid_priorities()
            elif "threshold" in error.lower():
                # Fix threshold issues
                self._fix_thresholds()
            elif "parallel" in error.lower():
                # Fix parallel execution issues
                self._fix_parallel_settings()
    
    def _fix_invalid_priorities(self):
        """Fix invalid priority values."""
        for task_type, priority in self.priority_config.default_priorities.items():
            if not isinstance(priority, int) or priority < 0 or priority > 100:
                # Set to default based on task type
                default_priority = self._get_default_priority_for_task(task_type)
                self.priority_config.set_task_priority(task_type, default_priority)
    
    def _fix_thresholds(self):
        """Fix threshold issues."""
        if (self.priority_config.high_priority_threshold <= 
            self.priority_config.medium_priority_threshold):
            self.priority_config.high_priority_threshold = (
                self.priority_config.medium_priority_threshold + 20
            )
        
        if (self.priority_config.medium_priority_threshold <= 
            self.priority_config.low_priority_threshold):
            self.priority_config.medium_priority_threshold = (
                self.priority_config.low_priority_threshold + 20
            )
    
    def _fix_parallel_settings(self):
        """Fix parallel execution settings."""
        if self.priority_config.enable_parallel_execution:
            if self.priority_config.max_parallel_tasks < 1:
                self.priority_config.max_parallel_tasks = 3
    
    def _get_default_priority_for_task(self, task_type: str) -> int:
        """Get default priority for a task type."""
        defaults = {
            'database': 100,
            'file': 90,
            'network': 80,
            'browser': 70,
            'custom': 60,
            'checkpoint': 50
        }
        return defaults.get(task_type, 50)
    
    def get_task_priority(self, task_type: str) -> int:
        """Get priority for a task type."""
        return self.priority_config.get_task_priority(task_type)
    
    def set_task_priority(self, task_type: str, priority: int):
        """Set priority for a task type."""
        self.priority_config.set_task_priority(task_type, priority)
    
    def get_ordered_tasks(self, tasks: List[str]) -> List[str]:
        """Get tasks ordered by priority."""
        return self.priority_config.get_tasks_by_priority(tasks)
    
    def get_task_timeout(self, task_type: str, base_timeout: float) -> float:
        """Get timeout for a task type."""
        return self.priority_config.get_timeout_for_task(task_type, base_timeout)
    
    def get_configuration(self) -> CleanupPriorityConfig:
        """Get the current priority configuration."""
        return self.priority_config
    
    def update_configuration(self, **kwargs):
        """Update priority configuration."""
        for key, value in kwargs.items():
            if hasattr(self.priority_config, key):
                setattr(self.priority_config, key, value)
                self.logger.debug(f"Updated priority config: {key} = {value}")
        
        # Re-validate after update
        self._validate_and_fix()
    
    def get_priority_statistics(self) -> Dict[str, Any]:
        """Get statistics about priority configuration."""
        priorities = list(self.priority_config.default_priorities.values())
        
        return {
            'total_task_types': len(self.priority_config.default_priorities),
            'priority_range': {
                'min': min(priorities) if priorities else 0,
                'max': max(priorities) if priorities else 0,
                'average': sum(priorities) / len(priorities) if priorities else 0
            },
            'high_priority_tasks': len([
                t for t, p in self.priority_config.default_priorities.items()
                if p >= self.priority_config.high_priority_threshold
            ]),
            'medium_priority_tasks': len([
                t for t, p in self.priority_config.default_priorities.items()
                if (self.priority_config.medium_priority_threshold <= p < 
                    self.priority_config.high_priority_threshold)
            ]),
            'low_priority_tasks': len([
                t for t, p in self.priority_config.default_priorities.items()
                if p < self.priority_config.medium_priority_threshold
            ]),
            'priority_groups': len(self.priority_config.priority_groups),
            'parallel_execution_enabled': self.priority_config.enable_parallel_execution,
            'ordering_strategy': self.priority_config.ordering_strategy.value
        }
