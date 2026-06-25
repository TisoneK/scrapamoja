"""
Priority ordering system for resource cleanup operations.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Callable, Set
from enum import Enum
from dataclasses import dataclass, field

from .resource_manager import ResourceType, ResourceCleanupTask


class CleanupPriority(Enum):
    """Priority levels for cleanup operations."""
    CRITICAL = 1    # Must be cleaned up first (data preservation)
    HIGH = 2        # Important resources (database connections)
    NORMAL = 3      # Standard resources (file handles)
    LOW = 4         # Less important (network connections)
    DEFERRED = 5    # Can be deferred (custom resources)


@dataclass
class PriorityRule:
    """Rule for determining cleanup priority."""
    resource_type: ResourceType
    priority: CleanupPriority
    condition: Optional[Callable[[Any], bool]] = None
    description: str = ""
    
    def matches(self, resource: Any) -> bool:
        """Check if this rule matches the given resource."""
        if self.condition is None:
            return True
        return self.condition(resource)


class PriorityOrderingSystem:
    """Manages priority ordering for resource cleanup."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._priority_rules: List[PriorityRule] = []
        self._custom_priorities: Dict[str, CleanupPriority] = {}
        self._default_priorities = {
            ResourceType.DATABASE: CleanupPriority.HIGH,
            ResourceType.FILE: CleanupPriority.NORMAL,
            ResourceType.NETWORK: CleanupPriority.LOW,
            ResourceType.CUSTOM: CleanupPriority.DEFERRED
        }
        self._lock = None
        
        # Initialize default rules
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default priority rules."""
        # Database rules
        self.add_rule(PriorityRule(
            resource_type=ResourceType.DATABASE,
            priority=CleanupPriority.CRITICAL,
            condition=lambda resource: hasattr(resource, 'in_transaction') and resource.in_transaction,
            description="Database connections in active transactions"
        ))
        
        self.add_rule(PriorityRule(
            resource_type=ResourceType.DATABASE,
            priority=CleanupPriority.HIGH,
            description="Standard database connections"
        ))
        
        # File rules
        self.add_rule(PriorityRule(
            resource_type=ResourceType.FILE,
            priority=CleanupPriority.CRITICAL,
            condition=lambda resource: hasattr(resource, 'name') and (
                '.tmp' in resource.name or 
                resource.name.endswith('.lock') or
                'checkpoint' in resource.name.lower()
            ),
            description="Critical files (temp files, locks, checkpoints)"
        ))
        
        self.add_rule(PriorityRule(
            resource_type=ResourceType.FILE,
            priority=CleanupPriority.HIGH,
            condition=lambda resource: hasattr(resource, 'mode') and 'w' in resource.mode,
            description="Open files for writing"
        ))
        
        self.add_rule(PriorityRule(
            resource_type=ResourceType.FILE,
            priority=CleanupPriority.NORMAL,
            description="Standard file handles"
        ))
        
        # Network rules
        self.add_rule(PriorityRule(
            resource_type=ResourceType.NETWORK,
            priority=CleanupPriority.HIGH,
            condition=lambda resource: hasattr(resource, 'ssl') and resource.ssl,
            description="SSL/TLS network connections"
        ))
        
        self.add_rule(PriorityRule(
            resource_type=ResourceType.NETWORK,
            priority=CleanupPriority.NORMAL,
            condition=lambda resource: hasattr(resource, 'family') and resource.family == 1,  # Unix socket
            description="Unix domain sockets"
        ))
        
        self.add_rule(PriorityRule(
            resource_type=ResourceType.NETWORK,
            priority=CleanupPriority.LOW,
            description="Standard network connections"
        ))
        
        # Custom rules
        self.add_rule(PriorityRule(
            resource_type=ResourceType.CUSTOM,
            priority=CleanupPriority.NORMAL,
            description="Custom resources"
        ))
    
    def add_rule(self, rule: PriorityRule):
        """Add a priority rule."""
        self._priority_rules.append(rule)
        self.logger.debug(f"Added priority rule: {rule.description}")
    
    def remove_rule(self, rule: PriorityRule):
        """Remove a priority rule."""
        if rule in self._priority_rules:
            self._priority_rules.remove(rule)
            self.logger.debug(f"Removed priority rule: {rule.description}")
    
    def set_custom_priority(self, resource_id: str, priority: CleanupPriority):
        """Set custom priority for a specific resource."""
        self._custom_priorities[resource_id] = priority
        self.logger.debug(f"Set custom priority for {resource_id}: {priority.name}")
    
    def remove_custom_priority(self, resource_id: str):
        """Remove custom priority for a resource."""
        if resource_id in self._custom_priorities:
            del self._custom_priorities[resource_id]
            self.logger.debug(f"Removed custom priority for {resource_id}")
    
    def get_priority(self, resource_task: ResourceCleanupTask, resource: Any = None) -> CleanupPriority:
        """
        Get the priority for a resource cleanup task.
        
        Args:
            resource_task: The resource cleanup task
            resource: The actual resource object (optional)
            
        Returns:
            The cleanup priority for this resource
        """
        # Check for custom priority first
        if resource_task.resource_id in self._custom_priorities:
            return self._custom_priorities[resource_task.resource_id]
        
        # Check rules for this resource type
        matching_rules = [
            rule for rule in self._priority_rules
            if rule.resource_type == resource_task.resource_type
        ]
        
        # Find the most specific matching rule
        for rule in matching_rules:
            if resource is not None and rule.matches(resource):
                return rule.priority
        
        # If no specific rule matches, use the first rule for this type
        if matching_rules:
            return matching_rules[0].priority
        
        # Fall back to default priority
        return self._default_priorities.get(resource_task.resource_type, CleanupPriority.NORMAL)
    
    def order_resources_by_priority(self, resource_tasks: List[ResourceCleanupTask], 
                                 resources: Optional[Dict[str, Any]] = None) -> List[ResourceCleanupTask]:
        """
        Order resource cleanup tasks by priority.
        
        Args:
            resource_tasks: List of resource cleanup tasks
            resources: Optional mapping of resource IDs to actual resources
            
        Returns:
            List of tasks ordered by cleanup priority
        """
        def get_sort_key(task: ResourceCleanupTask):
            resource = resources.get(task.resource_id) if resources else None
            priority = self.get_priority(task, resource)
            return (priority.value, task.resource_id)  # Use resource_id as tie-breaker
        
        # Sort by priority (lower value = higher priority)
        sorted_tasks = sorted(resource_tasks, key=get_sort_key)
        
        self.logger.debug(f"Ordered {len(sorted_tasks)} resources by priority")
        
        return sorted_tasks
    
    def create_priority_groups(self, resource_tasks: List[ResourceCleanupTask], 
                            resources: Optional[Dict[str, Any]] = None) -> Dict[CleanupPriority, List[ResourceCleanupTask]]:
        """
        Group resource cleanup tasks by priority.
        
        Args:
            resource_tasks: List of resource cleanup tasks
            resources: Optional mapping of resource IDs to actual resources
            
        Returns:
            Dictionary mapping priorities to lists of tasks
        """
        groups = {priority: [] for priority in CleanupPriority}
        
        for task in resource_tasks:
            resource = resources.get(task.resource_id) if resources else None
            priority = self.get_priority(task, resource)
            groups[priority].append(task)
        
        # Sort each group by resource ID for consistent ordering
        for priority in groups:
            groups[priority].sort(key=lambda t: t.resource_id)
        
        return groups
    
    def get_priority_statistics(self, resource_tasks: List[ResourceCleanupTask], 
                              resources: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get statistics about resource priorities."""
        priority_counts = {priority.value: 0 for priority in CleanupPriority}
        priority_details = {priority.value: [] for priority in CleanupPriority}
        
        for task in resource_tasks:
            resource = resources.get(task.resource_id) if resources else None
            priority = self.get_priority(task, resource)
            priority_counts[priority.value] += 1
            priority_details[priority.value].append(task.resource_id)
        
        return {
            'total_resources': len(resource_tasks),
            'priority_counts': priority_counts,
            'priority_details': priority_details,
            'custom_priorities': len(self._custom_priorities),
            'total_rules': len(self._priority_rules)
        }
    
    def validate_priority_ordering(self, resource_tasks: List[ResourceCleanupTask], 
                                resources: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Validate priority ordering and return any warnings.
        
        Args:
            resource_tasks: List of resource cleanup tasks
            resources: Optional mapping of resource IDs to actual resources
            
        Returns:
            List of validation warnings
        """
        warnings = []
        
        # Check for duplicate resource IDs
        resource_ids = [task.resource_id for task in resource_tasks]
        duplicates = set([rid for rid in resource_ids if resource_ids.count(rid) > 1])
        if duplicates:
            warnings.append(f"Duplicate resource IDs found: {duplicates}")
        
        # Check for resources without priority rules
        for task in resource_tasks:
            resource = resources.get(task.resource_id) if resources else None
            priority = self.get_priority(task, resource)
            
            if priority == CleanupPriority.NORMAL and task.resource_type not in self._default_priorities:
                warnings.append(f"Resource {task.resource_id} using default priority")
        
        # Check for too many critical resources
        critical_count = sum(1 for task in resource_tasks 
                          if self.get_priority(task, resources.get(task.resource_id) if resources else None) == CleanupPriority.CRITICAL)
        
        if critical_count > 10:
            warnings.append(f"High number of critical resources: {critical_count}")
        
        return warnings
    
    def create_priority_based_cleanup_plan(self, resource_tasks: List[ResourceCleanupTask], 
                                         resources: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a detailed cleanup plan based on priorities.
        
        Args:
            resource_tasks: List of resource cleanup tasks
            resources: Optional mapping of resource IDs to actual resources
            
        Returns:
            Detailed cleanup plan
        """
        # Order resources by priority
        ordered_tasks = self.order_resources_by_priority(resource_tasks, resources)
        
        # Create priority groups
        priority_groups = self.create_priority_groups(resource_tasks, resources)
        
        # Get statistics
        stats = self.get_priority_statistics(resource_tasks, resources)
        
        # Validate ordering
        warnings = self.validate_priority_ordering(resource_tasks, resources)
        
        # Create cleanup phases
        phases = []
        for priority in CleanupPriority:
            if priority_groups[priority]:
                phases.append({
                    'priority': priority.name,
                    'priority_value': priority.value,
                    'resource_count': len(priority_groups[priority]),
                    'resources': [task.resource_id for task in priority_groups[priority]],
                    'estimated_time': len(priority_groups[priority]) * 2.0  # Estimate 2s per resource
                })
        
        return {
            'total_resources': len(resource_tasks),
            'phases': phases,
            'ordered_resources': [task.resource_id for task in ordered_tasks],
            'statistics': stats,
            'warnings': warnings,
            'estimated_total_time': sum(phase['estimated_time'] for phase in phases)
        }
    
    def export_priority_rules(self) -> List[Dict[str, Any]]:
        """Export priority rules for inspection or modification."""
        return [
            {
                'resource_type': rule.resource_type.value,
                'priority': rule.priority.name,
                'priority_value': rule.priority.value,
                'description': rule.description,
                'has_condition': rule.condition is not None
            }
            for rule in self._priority_rules
        ]
    
    def import_priority_rules(self, rules_data: List[Dict[str, Any]]):
        """Import priority rules from data."""
        self._priority_rules.clear()
        
        for rule_data in rules_data:
            try:
                resource_type = ResourceType(rule_data['resource_type'])
                priority = CleanupPriority[rule_data['priority']]
                description = rule_data.get('description', '')
                
                rule = PriorityRule(
                    resource_type=resource_type,
                    priority=priority,
                    description=description
                )
                
                self.add_rule(rule)
                
            except (KeyError, ValueError) as e:
                self.logger.error(f"Error importing priority rule: {e}")
        
        self.logger.info(f"Imported {len(self._priority_rules)} priority rules")
    
    def reset_to_defaults(self):
        """Reset priority rules to defaults."""
        self._priority_rules.clear()
        self._custom_priorities.clear()
        self._initialize_default_rules()
        self.logger.info("Reset priority rules to defaults")
