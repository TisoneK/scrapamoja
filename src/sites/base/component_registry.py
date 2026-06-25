"""
Component registry for the modular site scraper template system.

This module provides centralized registration, discovery, and management of components
with version compatibility checking and metadata tracking.
"""

from typing import Dict, List, Optional, Any, Set, Type
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import json
from pathlib import Path

from src.observability.logger import get_logger

from .component_interface import BaseComponent, ComponentMetadata
from .component_manager import ComponentManager

logger = get_logger(__name__)


@dataclass
class ComponentRegistration:
    """Represents a component registration."""
    component_id: str
    component_class: Type[BaseComponent]
    metadata: ComponentMetadata
    registered_at: datetime
    registration_source: str  # manual, auto_discovery, plugin
    version_compatibility: Dict[str, str] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.registered_at is None:
            self.registered_at = datetime.utcnow()
        if self.version_compatibility is None:
            self.version_compatibility = {}
        if self.dependencies is None:
            self.dependencies = []
        if self.dependents is None:
            self.dependents = []


@dataclass
class RegistryStats:
    """Statistics for the component registry."""
    total_components: int = 0
    components_by_type: Dict[str, int] = field(default_factory=dict)
    components_by_source: Dict[str, int] = field(default_factory=dict)
    version_distribution: Dict[str, int] = field(default_factory=dict)
    dependency_graph: Dict[str, List[str]] = field(default_factory=dict)
    registration_timeline: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        if self.components_by_type is None:
            self.components_by_type = {}
        if self.components_by_source is None:
            self.components_by_source = {}
        if self.version_distribution is None:
            self.version_distribution = {}
        if self.dependency_graph is None:
            self.dependency_graph = {}
        if self.registration_timeline is None:
            self.registration_timeline = []


class ComponentRegistry:
    """Central registry for component management and discovery."""
    
    def __init__(self, component_manager: Optional[ComponentManager] = None):
        """
        Initialize the component registry.
        
        Args:
            component_manager: Component manager instance
        """
        self._registrations: Dict[str, ComponentRegistration] = {}
        self._component_manager = component_manager
        self._stats = RegistryStats()
        self._auto_discovery_paths: List[str] = []
        self._auto_discovery_enabled = True
        self._validation_enabled = True
        self._registry_file: Optional[Path] = None
        self._auto_save_enabled = True
        
    async def initialize(
        self,
        auto_discovery_paths: List[str] = None,
        auto_discovery: bool = True,
        registry_file: Optional[str] = None,
        auto_save: bool = True
    ) -> bool:
        """
        Initialize the component registry.
        
        Args:
            auto_discovery_paths: Paths for auto-discovery
            auto_discovery: Enable auto-discovery
            registry_file: File to save registry state
            auto_save: Enable auto-saving
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self._auto_discovery_paths = auto_discovery_paths or []
            self._auto_discovery_enabled = auto_discovery
            self._auto_save_enabled = auto_save
            
            if registry_file:
                self._registry_file = Path(registry_file)
                await self._load_registry_from_file()
            
            # Auto-discover components if enabled
            if auto_discovery and auto_discovery_paths:
                await self._auto_discover_components()
            
            # Build dependency graph
            await self._build_dependency_graph()
            
            logger.info("ComponentRegistry initialized", component_count=len(self._registrations))
            return True
            
        except Exception as e:
            logger.error("Failed to initialize ComponentRegistry", error=str(e))
            return False
    
    async def register_component(
        self,
        component_class: Type[BaseComponent],
        source: str = "manual",
        validate: bool = True
    ) -> bool:
        """
        Register a component class.
        
        Args:
            component_class: Component class to register
            source: Registration source
            validate: Validate component before registration
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            # Validate component if enabled
            if validate and not await self._validate_component_class(component_class):
                return False
            
            # Create temporary instance to get metadata
            temp_instance = component_class("temp", "temp", "1.0.0", "temp")
            component_id = temp_instance.component_id
            
            # Check if already registered
            if component_id in self._registrations:
                logger.debug("Component already registered", component_id=component_id)
                return False
            
            # Create registration
            registration = ComponentRegistration(
                component_id=component_id,
                component_class=component_class,
                metadata=temp_instance.metadata,
                registered_at=datetime.utcnow(),
                registration_source=source,
                dependencies=temp_instance.metadata.dependencies
            )
            
            # Add to registry
            self._registrations[component_id] = registration
            
            # Update statistics
            self._update_stats(registration, "registered")
            
            # Update dependency graph
            await self._update_dependency_graph(registration)
            
            # Auto-save if enabled
            if self._auto_save_enabled and self._registry_file:
                await self._save_registry_to_file()
            
            logger.info("Registered component", component_id=component_id, source=source)
            return True
            
        except Exception as e:
            logger.error("Failed to register component", class_name=component_class.__name__, error=str(e))
            return False
    
    async def unregister_component(self, component_id: str) -> bool:
        """
        Unregister a component.
        
        Args:
            component_id: Component ID to unregister
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if component_id not in self._registrations:
                logger.debug("Component not registered", component_id=component_id)
                return False
            
            # Check for dependents
            registration = self._registrations[component_id]
            if registration.dependents:
                logger.warning("Cannot unregister component: has dependents", 
                              component_id=component_id, dependents=registration.dependents)
                return False
            
            # Remove from registry
            del self._registrations[component_id]
            
            # Update statistics
            self._update_stats(registration, "unregistered")
            
            # Update dependency graph
            await self._update_dependency_graph(registration, remove=True)
            
            # Auto-save if enabled
            if self._auto_save_enabled and self._registry_file:
                await self._save_registry_to_file()
            
            logger.info("Unregistered component", component_id=component_id)
            return True
            
        except Exception as e:
            logger.error("Failed to unregister component", component_id=component_id, error=str(e))
            return False
    
    async def get_component(self, component_id: str) -> Optional[Type[BaseComponent]]:
        """
        Get a component class by ID.
        
        Args:
            component_id: Component ID
            
        Returns:
            Component class if found, None otherwise
        """
        registration = self._registrations.get(component_id)
        if registration:
            return registration.component_class
        return None
    
    async def get_component_metadata(self, component_id: str) -> Optional[ComponentMetadata]:
        """
        Get component metadata by ID.
        
        Args:
            component_id: Component ID
            
        Returns:
            Component metadata if found, None otherwise
        """
        registration = self._registrations.get(component_id)
        if registration:
            return registration.metadata
        return None
    
    async def find_components(
        self,
        component_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        source: Optional[str] = None
    ) -> List[str]:
        """
        Find components matching criteria.
        
        Args:
            component_type: Filter by component type
            tags: Filter by tags
            source: Filter by registration source
            
        Returns:
            List of matching component IDs
        """
        matching_components = []
        
        for component_id, registration in self._registrations.items():
            # Filter by component type
            if component_type and registration.metadata.component_type != component_type:
                continue
            
            # Filter by tags
            if tags and not any(tag in registration.metadata.tags for tag in tags):
                continue
            
            # Filter by source
            if source and registration.registration_source != source:
                continue
            
            matching_components.append(component_id)
        
        return matching_components
    
    async def get_dependencies(self, component_id: str) -> List[str]:
        """
        Get dependencies for a component.
        
        Args:
            component_id: Component ID
            
        Returns:
            List of dependency component IDs
        """
        registration = self._registrations.get(component_id)
        if registration:
            return registration.dependencies
        return []
    
    async def get_dependents(self, component_id: str) -> List[str]:
        """
        Get components that depend on a component.
        
        Args:
            component_id: Component ID
            
        Returns:
            List of dependent component IDs
        """
        registration = self._registrations.get(component_id)
        if registration:
            return registration.dependents
        return []
    
    async def check_compatibility(
        self,
        component_id: str,
        required_version: str
    ) -> bool:
        """
        Check version compatibility for a component.
        
        Args:
            component_id: Component ID
            required_version: Required version
            
        Returns:
            True if compatible, False otherwise
        """
        registration = self._registrations.get(component_id)
        if not registration:
            return False
        
        # Check version compatibility matrix
        compatibility = registration.version_compatibility.get(required_version)
        if compatibility is None:
            # Simple version match if no compatibility matrix
            return registration.metadata.version == required_version
        
        return compatibility == "compatible"
    
    async def validate_all_components(self) -> Dict[str, Dict[str, Any]]:
        """
        Validate all registered components.
        
        Returns:
            Validation results for all components
        """
        results = {}
        
        for component_id, registration in self._registrations.items():
            try:
                # Create temporary instance for validation
                temp_instance = registration.component_class("temp", "temp", "1.0.0", "temp")
                
                # Validate component
                is_valid = await temp_instance.validate()
                
                results[component_id] = {
                    "is_valid": is_valid,
                    "component_type": registration.metadata.component_type,
                    "version": registration.metadata.version,
                    "dependencies": registration.dependencies,
                    "source": registration.registration_source
                }
                
            except Exception as e:
                results[component_id] = {
                    "is_valid": False,
                    "error": str(e),
                    "component_type": registration.metadata.component_type,
                    "version": registration.metadata.version,
                    "dependencies": registration.dependencies,
                    "source": registration.registration_source
                }
        
        return results
    
    async def list_components(self) -> List[str]:
        """
        List all registered component IDs.
        
        Returns:
            List of component IDs
        """
        return list(self._registrations.keys())
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get registry statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "total_components": self._stats.total_components,
            "components_by_type": self._stats.components_by_type,
            "components_by_source": self._stats.components_by_source,
            "version_distribution": self._stats.version_distribution,
            "dependency_graph": self._stats.dependency_graph,
            "registration_timeline": self._stats.registration_timeline[-10:],  # Last 10 registrations
            "auto_discovery_enabled": self._auto_discovery_enabled,
            "validation_enabled": self._validation_enabled,
            "auto_save_enabled": self._auto_save_enabled,
            "registry_file": str(self._registry_file) if self._registry_file else None
        }
    
    async def export_registry(self, file_path: str) -> bool:
        """
        Export registry to file.
        
        Args:
            file_path: File path to export to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            export_data = {
                "version": "1.0.0",
                "exported_at": datetime.utcnow().isoformat(),
                "components": {}
            }
            
            for component_id, registration in self._registrations.items():
                export_data["components"][component_id] = {
                    "component_class": f"{registration.component_class.__module__}.{registration.component_class.__name__}",
                    "metadata": registration.metadata.__dict__,
                    "registered_at": registration.registered_at.isoformat(),
                    "registration_source": registration.registration_source,
                    "dependencies": registration.dependencies,
                    "version_compatibility": registration.version_compatibility
                }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default_flow_style=False)
            
            logger.info("Exported registry", file_path=file_path)
            return True
            
        except Exception as e:
            logger.error("Failed to export registry", file_path=file_path, error=str(e))
            return False
    
    async def import_registry(self, file_path: str, overwrite: bool = False) -> bool:
        """
        Import registry from file.
        
        Args:
            file_path: File path to import from
            overwrite: Overwrite existing registrations
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # Check version compatibility
            if import_data.get("version") != "1.0.0":
                logger.warning("Incompatible registry version", version=import_data.get('version'))
                return False
            
            # Clear existing registrations if overwrite
            if overwrite:
                self._registrations.clear()
            
            # Import components
            for component_id, component_data in import_data.get("components", {}).items():
                if component_id in self._registrations and not overwrite:
                    logger.debug("Component already exists, skipping import", component_id=component_id)
                    continue
                
                # Reconstruct registration
                metadata = ComponentMetadata(**component_data["metadata"])
                
                # Import component class
                module_name, class_name = component_data["component_class"].rsplit(".", 1)
                module = __import__(module_name)
                component_class = getattr(module, class_name)
                
                registration = ComponentRegistration(
                    component_id=component_id,
                    component_class=component_class,
                    metadata=metadata,
                    registered_at=datetime.fromisoformat(component_data["registered_at"]),
                    registration_source=component_data["registration_source"],
                    dependencies=component_data["dependencies"],
                    version_compatibility=component_data["version_compatibility"]
                )
                
                self._registrations[component_id] = registration
            
            # Rebuild statistics and dependency graph
            await self._rebuild_stats()
            await self._build_dependency_graph()
            
            logger.info("Imported registry", file_path=file_path)
            return True
            
        except Exception as e:
            logger.error("Failed to import registry", file_path=file_path, error=str(e))
            return False
    
    async def cleanup(self) -> None:
        """Clean up registry resources."""
        try:
            # Save registry if auto-save enabled
            if self._auto_save_enabled and self._registry_file:
                await self._save_registry_to_file()
            
            # Clear registrations
            self._registrations.clear()
            self._stats = RegistryStats()
            
            logger.info("ComponentRegistry cleanup completed")
            
        except Exception as e:
            logger.error("Error during ComponentRegistry cleanup", error=str(e))
    
    async def _validate_component_class(self, component_class: Type[BaseComponent]) -> bool:
        """Validate a component class."""
        try:
            # Check if it inherits from BaseComponent
            if not issubclass(component_class, BaseComponent):
                return False
            
            # Check required methods
            required_methods = ['initialize', 'execute', 'validate', 'cleanup']
            for method in required_methods:
                if not hasattr(component_class, method):
                    return False
            
            return True
            
        except Exception:
            return False
    
    async def _auto_discover_components(self) -> None:
        """Auto-discover components from configured paths."""
        for discovery_path in self._auto_discovery_paths:
            try:
                path = Path(discovery_path)
                if not path.exists():
                    continue
                
                # Look for Python files
                for component_file in path.rglob("*.py"):
                    if component_file.name.startswith("__"):
                        continue
                    
                    await self._inspect_component_file(component_file)
                    
            except Exception as e:
                logger.error("Error discovering components", discovery_path=discovery_path, error=str(e))
    
    async def _inspect_component_file(self, file_path: Path) -> None:
        """Inspect a Python file for components."""
        try:
            # Convert path to module name
            relative_path = file_path.relative_to(Path.cwd())
            module_name = str(relative_path.with_suffix("")).replace("/", ".").replace("\\", ".")
            
            # Import module
            module = __import__(module_name)
            
            # Look for component classes
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (obj != BaseComponent and 
                    issubclass(obj, BaseComponent) and 
                    obj.__module__ == module_name):
                    
                    await self.register_component(obj, "auto_discovery")
                    
        except Exception as e:
            logger.error("Error inspecting component file", file_path=str(file_path), error=str(e))
    
    async def _update_stats(self, registration: ComponentRegistration, action: str) -> None:
        """Update registry statistics."""
        if action == "registered":
            self._stats.total_components += 1
            
            # Update by type
            component_type = registration.metadata.component_type
            self._stats.components_by_type[component_type] = self._stats.components_by_type.get(component_type, 0) + 1
            
            # Update by source
            source = registration.registration_source
            self._stats.components_by_source[source] = self._stats.components_by_source.get(source, 0) + 1
            
            # Update version distribution
            version = registration.metadata.version
            self._stats.version_distribution[version] = self._stats.version_distribution.get(version, 0) + 1
            
            # Add to timeline
            self._stats.registration_timeline.append({
                "component_id": registration.component_id,
                "action": action,
                "timestamp": registration.registered_at.isoformat(),
                "source": registration.registration_source,
                "version": registration.metadata.version
            })
            
        elif action == "unregistered":
            self._stats.total_components -= 1
            
            # Update by type
            component_type = registration.metadata.component_type
            if component_type in self._stats.components_by_type:
                self._stats.components_by_type[component_type] -= 1
                if self._stats.components_by_type[component_type] == 0:
                    del self._stats.components_by_type[component_type]
            
            # Update by source
            source = registration.registration_source
            if source in self._stats.components_by_source:
                self._stats.components_by_source[source] -= 1
                if self._stats.components_by_source[source] == 0:
                    del self._stats.components_by_source[source]
            
            # Update version distribution
            version = registration.metadata.version
            if version in self._stats.version_distribution:
                self._stats.version_distribution[version] -= 1
                if self._stats.version_distribution[version] == 0:
                    del self._stats.version_distribution[version]
            
            # Add to timeline
            self._stats.registration_timeline.append({
                "component_id": registration.component_id,
                "action": action,
                "timestamp": datetime.utcnow().isoformat(),
                "source": registration.registration_source,
                "version": registration.metadata.version
            })
    
    async def _update_dependency_graph(self, registration: ComponentRegistration, remove: bool = False) -> None:
        """Update the dependency graph."""
        if remove:
            # Remove from graph
            if registration.component_id in self._stats.dependency_graph:
                del self._stats.dependency_graph[registration.component_id]
            
            # Remove from dependents
            for dep_id in registration.dependencies:
                if dep_id in self._registrations:
                    if registration.component_id in self._registrations[dep_id].dependents:
                        self._registrations[dep_id].dependents.remove(registration.component_id)
        else:
            # Add to graph
            self._stats.dependency_graph[registration.component_id] = registration.dependencies
            
            # Update dependents
            for dep_id in registration.dependencies:
                if dep_id in self._registrations:
                    if registration.component_id not in self._registrations[dep_id].dependents:
                        self._registrations[dep_id].dependents.append(registration.component_id)
    
    async def _build_dependency_graph(self) -> None:
        """Build the complete dependency graph."""
        self._stats.dependency_graph.clear()
        
        for registration in self._registrations.values():
            self._stats.dependency_graph[registration.component_id] = registration.dependencies
            
            # Update dependents
            for dep_id in registration.dependencies:
                if dep_id in self._registrations:
                    if registration.component_id not in self._registrations[dep_id].dependents:
                        self._registrations[dep_id].dependents.append(registration.component_id)
    
    async def _rebuild_stats(self) -> None:
        """Rebuild statistics from current registrations."""
        self._stats = RegistryStats()
        
        for registration in self._registrations.values():
            await self._update_stats(registration, "registered")
    
    async def _save_registry_to_file(self) -> None:
        """Save registry to file."""
        if not self._registry_file:
            return
        
        try:
            # Ensure directory exists
            self._registry_file.parent.mkdir(parents=True, exist_ok=True)
            
            export_data = {
                "version": "1.0.0",
                "saved_at": datetime.utcnow().isoformat(),
                "components": {}
            }
            
            for component_id, registration in self._registrations.items():
                export_data["components"][component_id] = {
                    "component_class": f"{registration.component_class.__module__}.{registration.component_class.__name__}",
                    "metadata": registration.metadata.__dict__,
                    "registered_at": registration.registered_at.isoformat(),
                    "registration_source": registration.registration_source,
                    "dependencies": registration.dependencies,
                    "version_compatibility": registration.version_compatibility
                }
            
            with open(self._registry_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default_flow_style=False)
                
        except Exception as e:
            logger.error("Failed to save registry to file", error=str(e))
    
    async def _load_registry_from_file(self) -> None:
        """Load registry from file."""
        if not self._registry_file or not self._registry_file.exists():
            return
        
        try:
            with open(self._registry_file, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # Check version compatibility
            if import_data.get("version") != "1.0.0":
                logger.warning("Incompatible registry version", version=import_data.get('version'))
                return
            
            # Import components
            for component_id, component_data in import_data.get("components", {}).items():
                metadata = ComponentMetadata(**component_data["metadata"])
                
                # Import component class
                module_name, class_name = component_data["component_class"].rsplit(".", 1)
                module = __import__(module_name)
                component_class = getattr(module, class_name)
                
                registration = ComponentRegistration(
                    component_id=component_id,
                    component_class=component_class,
                    metadata=metadata,
                    registered_at=datetime.fromisoformat(component_data["registered_at"]),
                    registration_source=component_data["registration_source"],
                    dependencies=component_data["dependencies"],
                    version_compatibility=component_data["version_compatibility"]
                )
                
                self._registrations[component_id] = registration
            
            # Rebuild statistics and dependency graph
            await self._rebuild_stats()
            await self._build_dependency_graph()
            
        except Exception as e:
            logger.error("Failed to load registry from file", error=str(e))


class RegistryError(Exception):
    """Exception raised when registry operations fail."""
    pass


class ComponentNotFoundError(RegistryError):
    """Exception raised when a component is not found."""
    pass


class RegistrationError(RegistryError):
    """Exception raised when registration fails."""
    pass


class CompatibilityError(RegistryError):
    """Exception raised when version compatibility check fails."""
    pass
