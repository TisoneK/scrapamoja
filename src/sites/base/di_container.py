"""
Dependency injection container for the modular site scraper template system.

This module provides a lightweight dependency injection container that supports
constructor injection, method injection, and lifecycle management for components.
"""

from typing import Dict, Any, List, Optional, Type, Callable, Union, get_type_hints
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import inspect
from enum import Enum
import weakref

from src.observability.logger import get_logger
from .component_interface import BaseComponent, ComponentContext

# Module logger
logger = get_logger(__name__)


class LifetimeScope(Enum):
    """Dependency lifetime scopes."""
    TRANSIENT = "transient"  # New instance every time
    SINGLETON = "singleton"  # Single instance for container lifetime
    SCOPED = "scoped"  # Single instance per scope


@dataclass
class DependencyDefinition:
    """Definition of a dependency."""
    interface: Type
    implementation: Optional[Type] = None
    lifetime: LifetimeScope = LifetimeScope.TRANSIENT
    factory: Optional[Callable] = None
    instance: Optional[Any] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class InjectionContext:
    """Context for dependency injection operations."""
    scope_id: str
    created_at: Optional[datetime] = None
    parent_context: Optional['DIContainer'] = None
    components: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class DIContainer:
    """Dependency injection container for component management."""
    
    def __init__(self, container_id: str = "default"):
        """
        Initialize the DI container.
        
        Args:
            container_id: Container identifier
        """
        self.container_id = container_id
        self._dependencies: Dict[str, DependencyDefinition] = {}
        self._contexts: Dict[str, InjectionContext] = {}
        self._current_scope: Optional[str] = None
        self._auto_dispose: bool = True
        self._enable_circular_dependencies: bool = False
        self._creation_stack: List[str] = []
        
        # Register self for self-injection
        self.register_instance("container", self, LifetimeScope.SINGLETON)
    
    def register(
        self,
        interface: Type,
        implementation: Optional[Type] = None,
        lifetime: LifetimeScope = LifetimeScope.TRANSIENT,
        factory: Optional[Callable] = None,
        name: Optional[str] = None
    ) -> str:
        """
        Register a dependency.
        
        Args:
            interface: Interface type
            implementation: Implementation class
            lifetime: Lifetime scope
            factory: Factory function
            name: Dependency name (auto-generated if None)
            
        Returns:
            Dependency name
        """
        try:
            # Generate name if not provided
            if name is None:
                name = interface.__name__
            
            # Check for existing registration
            if name in self._dependencies:
                raise ValueError(f"Dependency '{name}' already registered")
            
            # Validate parameters
            if implementation is None and factory is None:
                raise ValueError(f"Either implementation or factory must be provided for '{name}'")
            
            # Create dependency definition
            dependency = DependencyDefinition(
                interface=interface,
                implementation=implementation,
                lifetime=lifetime,
                factory=factory
            )
            
            self._dependencies[name] = dependency
            
            logger.debug("Registered dependency", name=name, interface=interface.__name__)
            return name
        
        except Exception as e:
            logger.error("Failed to register dependency", error=str(e))
            raise
    
    def register_instance(
        self,
        name: str,
        instance: Any,
        lifetime: LifetimeScope = LifetimeScope.TRANSIENT
    ) -> str:
        """
        Register an instance as a dependency.
        
        Args:
            name: Dependency name
            instance: Instance to register
            lifetime: Lifetime scope
            
        Returns:
            Dependency name
        """
        try:
            # Check for existing registration
            if name in self._dependencies:
                raise ValueError(f"Dependency '{name}' already registered")
            
            # Create dependency definition
            dependency = DependencyDefinition(
                interface=type(instance),
                instance=instance,
                lifetime=lifetime
            )
            
            self._dependencies[name] = dependency
            
            logger.debug("Registered instance", name=name)
            return name
        
        except Exception as e:
            logger.error("Failed to register instance", error=str(e))
            raise
    
    def create_scope(self, scope_id: str) -> 'DIContainer':
        """
        Create a new injection scope.
        
        Args:
            scope_id: Scope identifier
            
        Returns:
            New container instance for the scope
        """
        try:
            # Create child container
            child_container = DIContainer(f"{self.container_id}.{scope_id}")
            
            # Copy dependencies
            child_container._dependencies = self._dependencies.copy()
            
            # Set parent context
            parent_context = self._get_current_context()
            child_context = InjectionContext(
                scope_id=scope_id,
                parent_context=self,
                created_at=datetime.utcnow()
            )
            
            child_container._current_scope = scope_id
            child_container._contexts[scope_id] = child_context
            
            return child_container
            
        except Exception as e:
            logger.error("Failed to create scope", scope_id=scope_id, error=str(e))
            raise
    
    def get(self, dependency_name: str) -> Any:
        """
        Get a dependency instance.
        
        Args:
            dependency_name: Name of dependency
            
        Returns:
            Dependency instance
        """
        try:
            # Check if dependency exists
            if dependency_name not in self._dependencies:
                raise ValueError(f"Dependency '{dependency_name}' not registered")
            
            dependency = self._dependencies[dependency_name]
            
            # Handle different lifetime scopes
            if dependency.lifetime == LifetimeScope.SINGLETON:
                return self._get_singleton_instance(dependency)
            elif dependency.lifetime == LifetimeScope.SCOPED:
                return self._get_scoped_instance(dependency)
            else:  # TRANSIENT
                return self._get_transient_instance(dependency)
                
        except Exception as e:
            logger.error("Failed to get dependency", dependency_name=dependency_name, error=str(e))
            raise
    
    async def get_async(self, dependency_name: str) -> Any:
        """
        Get a dependency instance asynchronously.
        
        Args:
            dependency_name: Name of dependency
            
        Returns:
            Dependency instance
        """
        return self.get(dependency_name)
    
    def inject_into(self, target: Any, method_name: Optional[str] = None) -> Any:
        """
        Inject dependencies into a target object or method.
        
        Args:
            target: Target object or class
            method_name: Method name (if injecting into method)
            
        Returns:
            Injected target or method
        """
        try:
            if method_name:
                # Inject into method
                return self._inject_into_method(target, method_name)
            else:
                # Inject into class/object
                return self._inject_into_object(target)
                
        except Exception as e:
            logger.error("Failed to inject dependencies", error=str(e))
            raise
    
    def resolve_dependencies(self, dependency_names: List[str]) -> Dict[str, Any]:
        """
        Resolve multiple dependencies at once.
        
        Args:
            dependency_names: List of dependency names
            
        Returns:
            Dictionary of resolved dependencies
        """
        try:
            resolved = {}
            
            for name in dependency_names:
                resolved[name] = self.get(name)
            
            return resolved
            
        except Exception as e:
            logger.error("Failed to resolve dependencies", error=str(e))
            raise
    
    def has_dependency(self, dependency_name: str) -> bool:
        """
        Check if a dependency is registered.
        
        Args:
            dependency_name: Dependency name
            
        Returns:
            True if registered, False otherwise
        """
        return dependency_name in self._dependencies
    
    async def validate_dependencies(self) -> Dict[str, List[str]]:
        """
        Validate all dependencies for circular references.
        
        Returns:
            Validation results
        """
        try:
            results = {}
            
            for name, dependency in self._dependencies.items():
                errors = []
                
                # Check for circular dependencies
                if self._check_circular_dependency(name, set()):
                    errors.append(f"Circular dependency detected")
                
                # Check for missing dependencies
                for dep_name in dependency.dependencies:
                    if dep_name not in self._dependencies:
                        errors.append(f"Missing dependency: {dep_name}")
                
                results[name] = errors
            
            return results
            
        except Exception as e:
            logger.error("Failed to validate dependencies", error=str(e))
            return {}
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get container statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "container_id": self.container_id,
            "total_dependencies": len(self._dependencies),
            "dependencies_by_lifetime": {
                "transient": len([d for d in self._dependencies.values() if d.lifetime == LifetimeScope.TRANSIENT]),
                "singleton": len([d for d in self._dependencies.values() if d.lifetime == LifetimeScope.SINGLETON]),
                "scoped": len([d for d in self._dependencies.values() if d.lifetime == LifetimeScope.SCOPED])
            },
            "active_scopes": len(self._contexts),
            "current_scope": self._current_scope,
            "auto_dispose": self._auto_dispose,
            "circular_dependencies_enabled": self._enable_circular_dependencies
        }
    
    async def cleanup(self) -> None:
        """Clean up container resources."""
        try:
            # Clean up singleton instances
            for dependency in self._dependencies.values():
                if dependency.lifetime == LifetimeScope.SINGLETON and dependency.instance:
                    if hasattr(dependency.instance, 'cleanup'):
                        try:
                            if inspect.iscoroutinefunction(dependency.instance.cleanup):
                                await dependency.instance.cleanup()
                            else:
                                dependency.instance.cleanup()
                        except Exception as e:
                            logger.error("Error cleaning up singleton", interface=dependency.interface.__name__, error=str(e))
                    dependency.instance = None
            
            # Clear contexts
            self._contexts.clear()
            self._current_scope = None
            
            # Clear dependencies
            self._dependencies.clear()
            
            logger.debug("DIContainer cleanup completed", container_id=self.container_id)
        
        except Exception as e:
            logger.error("Error during DIContainer cleanup", error=str(e))
    
    def _get_current_context(self) -> Optional[InjectionContext]:
        """Get the current injection context."""
        if self._current_scope and self._current_scope in self._contexts:
            return self._contexts[self._current_scope]
        return None
    
    def _get_singleton_instance(self, dependency: DependencyDefinition) -> Any:
        """Get or create a singleton instance."""
        if dependency.instance is None:
            if dependency.factory:
                dependency.instance = dependency.factory()
            else:
                dependency.instance = dependency.implementation()
            
            dependency.created_at = datetime.utcnow()
        
        return dependency.instance
    
    def _get_scoped_instance(self, dependency: DependencyDefinition) -> Any:
        """Get or create a scoped instance."""
        context = self._get_current_context()
        if not context:
            raise ValueError("No active scope for scoped dependency")
        
        # Check if instance exists in context
        if dependency.instance_id in context.components:
            return context.components[dependency.instance_id]
        
        # Create new instance
        if dependency.factory:
            instance = dependency.factory()
        else:
            instance = dependency.implementation()
        
        # Store in context
        instance_id = f"{dependency.interface.__name__}_{context.scope_id}"
        dependency.instance_id = instance_id
        dependency.instance = instance
        dependency.created_at = datetime.utcnow()
        
        context.components[instance_id] = instance
        
        # Set up cleanup when context is disposed
        if hasattr(context, 'parent_context'):
            # In a real implementation, we'd use weak references
            pass
        
        return instance
    
    def _get_transient_instance(self, dependency: DependencyDefinition) -> Any:
        """Get or create a transient instance."""
        if dependency.factory:
            return dependency.factory()
        elif dependency.instance:
            instance = dependency.instance
            dependency.instance = None  # Clear for next transient request
            return instance
        else:
            return dependency.implementation()
    
    def _inject_into_object(self, target: Any) -> Any:
        """Inject dependencies into an object."""
        try:
            # Get constructor parameters
            init_signature = inspect.signature(target.__init__)
            
            # Prepare arguments
            kwargs = {}
            
            for param_name, param in init_signature.parameters.items():
                if param_name == 'self':
                    continue
                
                param_type = param.annotation
                if param_type == inspect.Parameter.empty:
                    continue
                
                # Try to resolve dependency
                if self.has_dependency(param_name):
                    kwargs[param_name] = self.get(param_name)
            
            # Create new instance with injected dependencies
            if kwargs:
                # Create new class with injected dependencies
                class_name = f"Injected{target.__class__.__name__}"
                injected_class = type(class_name, (target.__class__,), {
                    '__init__': lambda self, **kwargs: super(target.__class__, self).__init__(**kwargs)
                })
                return injected_class()
            else:
                return target
                
        except Exception as e:
            logger.error("Failed to inject into object", error=str(e))
            raise
    
    def _inject_into_method(self, target: Any, method_name: str) -> Callable:
        """Inject dependencies into a method."""
        try:
            method = getattr(target, method_name)
            
            # Create wrapper with dependency injection
            def wrapper(*args, **kwargs):
                # Get method signature
                sig = inspect.signature(method)
                
                # Resolve dependencies for parameters
                bound_args = inspect.signature(method).bind_partial(*args)
                bound_kwargs = {}
                
                for param_name, param in sig.parameters.items():
                    if param_name == 'self':
                        continue
                    
                    if param.annotation != inspect.Parameter.empty:
                        if self.has_dependency(param_name):
                            bound_kwargs[param_name] = self.get(param_name)
                
                # Call original method with injected dependencies
                return method(*bound_args.args, **bound_kwargs)
            
            return wrapper
            
        except Exception as e:
            logger.error("Failed to inject into method", method_name=method_name, error=str(e))
            raise
    
    def _check_circular_dependency(self, dependency_name: str, visited: Set[str]) -> bool:
        """Check for circular dependencies."""
        if dependency_name in visited:
            return True
        
        visited.add(dependency_name)
        
        dependency = self._dependencies.get(dependency_name)
        if dependency:
            for dep_name in dependency.dependencies:
                if self._check_circular_dependency(dep_name, visited.copy()):
                    return True
        
        visited.remove(dependency_name)
        return False


class DIContainerError(Exception):
    """Exception raised when DI container operations fail."""
    pass


class DependencyNotFoundError(DIContainerError):
    """Exception raised when a dependency is not found."""
    pass


class CircularDependencyError(DIContainerError):
    """Exception raised when circular dependencies are detected."""
    pass


class InjectionError(DIContainerError):
    """Exception raised when dependency injection fails."""
    pass
