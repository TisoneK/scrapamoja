"""
Component manager for the modular site scraper template system.

This module provides centralized management of components, including discovery,
instantiation, lifecycle management, and dependency resolution.
"""

from typing import Dict, List, Optional, Any, Type, Set
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import importlib
import inspect
from pathlib import Path

from .component_interface import BaseComponent, ComponentMetadata, ComponentContext, ComponentResult


@dataclass
class ComponentInstance:
    """Represents an instantiated component."""
    component: BaseComponent
    instance_id: str
    created_at: datetime
    last_used: datetime
    usage_count: int = 0
    is_active: bool = True
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.last_used is None:
            self.last_used = datetime.utcnow()


@dataclass
class ComponentDependency:
    """Represents a dependency between components."""
    component_id: str
    required_version: str
    optional: bool = False
    alternative_components: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.alternative_components is None:
            self.alternative_components = []


@dataclass
class ComponentLifecycleEvent:
    """Event for component lifecycle changes."""
    event_type: str  # created, initialized, destroyed, error
    component_id: str
    instance_id: str
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class ComponentManager:
    """Manages component discovery, instantiation, and lifecycle."""
    
    def __init__(self):
        """Initialize the component manager."""
        self._registered_components: Dict[str, Type[BaseComponent]] = {}
        self._active_instances: Dict[str, ComponentInstance] = {}
        self._component_dependencies: Dict[str, List[ComponentDependency]] = {}
        self._lifecycle_events: List[ComponentLifecycleEvent] = []
        self._discovery_paths: List[str] = []
        self._auto_discovery_enabled = True
        self._max_instances_per_component = 10
        self._cleanup_interval_seconds = 300  # 5 minutes
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def initialize(self, discovery_paths: List[str] = None) -> bool:
        """
        Initialize the component manager.
        
        Args:
            discovery_paths: Paths to search for components
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            if discovery_paths:
                self._discovery_paths = discovery_paths
            
            # Auto-discover components if enabled
            if self._auto_discovery_enabled:
                await self._discover_components()
            
            # Start cleanup task
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            print(f"ComponentManager initialized with {len(self._registered_components)} components")
            return True
            
        except Exception as e:
            print(f"Failed to initialize ComponentManager: {str(e)}")
            return False
    
    async def register_component(self, component_class: Type[BaseComponent]) -> bool:
        """
        Register a component class.
        
        Args:
            component_class: Component class to register
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            # Validate component class
            if not issubclass(component_class, BaseComponent):
                raise ValueError(f"Component {component_class.__name__} must inherit from BaseComponent")
            
            # Create temporary instance to get metadata
            temp_instance = component_class("temp", "temp", "1.0.0", "temp")
            component_id = temp_instance.component_id
            
            # Check if already registered
            if component_id in self._registered_components:
                print(f"Component {component_id} already registered")
                return False
            
            # Register component
            self._registered_components[component_id] = component_class
            
            # Extract dependencies
            dependencies = await self._extract_dependencies(temp_instance)
            self._component_dependencies[component_id] = dependencies
            
            # Log lifecycle event
            await self._log_lifecycle_event("registered", component_id, "", {
                "component_class": component_class.__name__,
                "dependencies": [dep.component_id for dep in dependencies]
            })
            
            print(f"Registered component: {component_id}")
            return True
            
        except Exception as e:
            print(f"Failed to register component {component_class.__name__}: {str(e)}")
            return False
    
    async def create_instance(
        self,
        component_id: str,
        context: ComponentContext,
        instance_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Create an instance of a component.
        
        Args:
            component_id: ID of component to instantiate
            context: Component context
            instance_id: Optional instance ID
            
        Returns:
            Instance ID if successful, None otherwise
        """
        try:
            # Check if component is registered
            if component_id not in self._registered_components:
                raise ValueError(f"Component {component_id} not registered")
            
            # Check instance limit
            instance_count = sum(1 for inst in self._active_instances.values() 
                              if inst.component.component_id == component_id and inst.is_active)
            if instance_count >= self._max_instances_per_component:
                raise ValueError(f"Maximum instances reached for component {component_id}")
            
            # Resolve dependencies
            await self._resolve_dependencies(component_id)
            
            # Create instance ID if not provided
            if not instance_id:
                instance_id = f"{component_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
            
            # Check if instance already exists
            if instance_id in self._active_instances:
                raise ValueError(f"Instance {instance_id} already exists")
            
            # Create component instance
            component_class = self._registered_components[component_id]
            component = component_class(
                component_id,
                f"Instance of {component_id}",
                "1.0.0",
                f"Created instance of {component_id}"
            )
            
            # Initialize component
            if not await component.initialize(context):
                raise ValueError(f"Failed to initialize component {component_id}")
            
            # Create instance record
            instance = ComponentInstance(
                component=component,
                instance_id=instance_id,
                created_at=datetime.utcnow(),
                last_used=datetime.utcnow()
            )
            
            # Store instance
            self._active_instances[instance_id] = instance
            
            # Log lifecycle event
            await self._log_lifecycle_event("created", component_id, instance_id)
            
            print(f"Created instance: {instance_id} of component {component_id}")
            return instance_id
            
        except Exception as e:
            print(f"Failed to create instance of component {component_id}: {str(e)}")
            return None
    
    async def get_instance(self, instance_id: str) -> Optional[BaseComponent]:
        """
        Get a component instance by ID.
        
        Args:
            instance_id: Instance ID
            
        Returns:
            Component instance if found, None otherwise
        """
        instance = self._active_instances.get(instance_id)
        if instance and instance.is_active:
            instance.last_used = datetime.utcnow()
            instance.usage_count += 1
            return instance.component
        return None
    
    async def destroy_instance(self, instance_id: str) -> bool:
        """
        Destroy a component instance.
        
        Args:
            instance_id: Instance ID to destroy
            
        Returns:
            True if successful, False otherwise
        """
        try:
            instance = self._active_instances.get(instance_id)
            if not instance:
                print(f"Instance {instance_id} not found")
                return False
            
            # Cleanup component
            await instance.component.cleanup()
            
            # Mark as inactive
            instance.is_active = False
            
            # Remove from active instances
            del self._active_instances[instance_id]
            
            # Log lifecycle event
            await self._log_lifecycle_event("destroyed", instance.component.component_id, instance_id)
            
            print(f"Destroyed instance: {instance_id}")
            return True
            
        except Exception as e:
            print(f"Failed to destroy instance {instance_id}: {str(e)}")
            return False
    
    async def get_component_info(self, component_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a component.
        
        Args:
            component_id: Component ID
            
        Returns:
            Component information if found, None otherwise
        """
        component_class = self._registered_components.get(component_id)
        if not component_class:
            return None
        
        # Create temporary instance to get metadata
        temp_instance = component_class("temp", "temp", "1.0.0", "temp")
        
        # Get active instances
        active_instances = [
            inst.instance_id for inst in self._active_instances.values()
            if inst.component.component_id == component_id and inst.is_active
        ]
        
        return {
            "component_id": component_id,
            "component_class": component_class.__name__,
            "metadata": temp_instance.metadata.__dict__,
            "dependencies": [dep.__dict__ for dep in self._component_dependencies.get(component_id, [])],
            "active_instances": active_instances,
            "registered_at": datetime.utcnow().isoformat()
        }
    
    async def list_components(self) -> List[str]:
        """
        List all registered component IDs.
        
        Returns:
            List of component IDs
        """
        return list(self._registered_components.keys())
    
    async def list_instances(self) -> List[str]:
        """
        List all active instance IDs.
        
        Returns:
            List of instance IDs
        """
        return [inst_id for inst_id, inst in self._active_instances.items() if inst.is_active]
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get component manager statistics.
        
        Returns:
            Statistics dictionary
        """
        total_instances = len(self._active_instances)
        active_instances = sum(1 for inst in self._active_instances.values() if inst.is_active)
        
        component_stats = {}
        for component_id in self._registered_components:
            component_instances = [
                inst for inst in self._active_instances.values()
                if inst.component.component_id == component_id and inst.is_active
            ]
            component_stats[component_id] = {
                "active_instances": len(component_instances),
                "total_usage": sum(inst.usage_count for inst in component_instances),
                "last_used": max((inst.last_used for inst in component_instances), default=None)
            }
        
        return {
            "registered_components": len(self._registered_components),
            "total_instances": total_instances,
            "active_instances": active_instances,
            "component_stats": component_stats,
            "lifecycle_events": len(self._lifecycle_events),
            "auto_discovery_enabled": self._auto_discovery_enabled,
            "discovery_paths": self._discovery_paths
        }
    
    async def _discover_components(self) -> None:
        """Auto-discover components from configured paths."""
        for discovery_path in self._discovery_paths:
            try:
                path = Path(discovery_path)
                if not path.exists():
                    continue
                
                # Look for Python files
                for py_file in path.rglob("*.py"):
                    if py_file.name.startswith("__"):
                        continue
                    
                    # Try to import and inspect the module
                    await self._inspect_module_file(py_file)
                    
            except Exception as e:
                print(f"Error discovering components in {discovery_path}: {str(e)}")
    
    async def _inspect_module_file(self, file_path: Path) -> None:
        """Inspect a Python file for component classes."""
        try:
            # Convert path to module name
            relative_path = file_path.relative_to(Path.cwd())
            module_name = str(relative_path.with_suffix("")).replace("/", ".").replace("\\", ".")
            
            # Import module
            module = importlib.import_module(module_name)
            
            # Look for component classes
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (obj != BaseComponent and 
                    issubclass(obj, BaseComponent) and 
                    obj.__module__ == module_name):
                    
                    await self.register_component(obj)
                    
        except Exception as e:
            print(f"Error inspecting {file_path}: {str(e)}")
    
    async def _extract_dependencies(self, component: BaseComponent) -> List[ComponentDependency]:
        """Extract dependencies from a component."""
        dependencies = []
        
        # Get dependencies from metadata
        for dep_id in component.metadata.dependencies:
            dependencies.append(ComponentDependency(
                component_id=dep_id,
                required_version="1.0.0",  # Default version
                optional=False
            ))
        
        return dependencies
    
    async def _resolve_dependencies(self, component_id: str) -> bool:
        """Resolve dependencies for a component."""
        dependencies = self._component_dependencies.get(component_id, [])
        
        for dep in dependencies:
            if dep.component_id not in self._registered_components:
                if dep.optional:
                    print(f"Optional dependency {dep.component_id} not found for {component_id}")
                    continue
                else:
                    raise ValueError(f"Required dependency {dep.component_id} not found for {component_id}")
        
        return True
    
    async def _cleanup_loop(self) -> None:
        """Background task for cleaning up inactive instances."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval_seconds)
                await self._cleanup_inactive_instances()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in cleanup loop: {str(e)}")
    
    async def _cleanup_inactive_instances(self) -> None:
        """Clean up inactive instances."""
        current_time = datetime.utcnow()
        instances_to_remove = []
        
        for instance_id, instance in self._active_instances.items():
            # Remove instances inactive for more than 1 hour
            if (current_time - instance.last_used).total_seconds() > 3600:
                instances_to_remove.append(instance_id)
        
        for instance_id in instances_to_remove:
            await self.destroy_instance(instance_id)
    
    async def _log_lifecycle_event(
        self,
        event_type: str,
        component_id: str,
        instance_id: str,
        details: Dict[str, Any] = None
    ) -> None:
        """Log a lifecycle event."""
        event = ComponentLifecycleEvent(
            event_type=event_type,
            component_id=component_id,
            instance_id=instance_id,
            timestamp=datetime.utcnow(),
            details=details or {}
        )
        
        self._lifecycle_events.append(event)
        
        # Keep only last 1000 events
        if len(self._lifecycle_events) > 1000:
            self._lifecycle_events = self._lifecycle_events[-1000:]
    
    async def cleanup(self) -> None:
        """Clean up component manager resources."""
        try:
            # Cancel cleanup task
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # Destroy all active instances
            instances_to_destroy = list(self._active_instances.keys())
            for instance_id in instances_to_destroy:
                await self.destroy_instance(instance_id)
            
            print("ComponentManager cleanup completed")
            
        except Exception as e:
            print(f"Error during ComponentManager cleanup: {str(e)}")


class ComponentManagerError(Exception):
    """Exception raised when component manager operations fail."""
    pass


class ComponentNotFoundError(ComponentManagerError):
    """Exception raised when a component is not found."""
    pass


class DependencyResolutionError(ComponentManagerError):
    """Exception raised when dependency resolution fails."""
    pass
