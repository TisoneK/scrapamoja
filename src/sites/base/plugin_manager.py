"""
Plugin manager base for the modular site scraper template system.

This module provides the foundation for plugin discovery, loading, lifecycle management,
and hook execution for extending scraper functionality.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import importlib
import inspect
from pathlib import Path
import json

from .component_interface import BaseComponent, ComponentContext, ComponentResult


@dataclass
class PluginMetadata:
    """Metadata for a plugin."""
    plugin_id: str
    name: str
    version: str
    description: str
    author: str = "Unknown"
    entry_point: str = ""
    dependencies: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    hooks: List[str] = field(default_factory=list)
    min_framework_version: str = "1.0.0"
    max_framework_version: str = "2.0.0"
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.permissions is None:
            self.permissions = []
        if self.hooks is None:
            self.hooks = []
        if self.tags is None:
            self.tags = []


@dataclass
class PluginInstance:
    """Represents an instantiated plugin."""
    plugin_id: str
    instance: Any
    metadata: PluginMetadata
    loaded_at: datetime
    last_used: datetime
    is_active: bool = True
    execution_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    
    def __post_init__(self):
        if self.loaded_at is None:
            self.loaded_at = datetime.utcnow()
        if self.last_used is None:
            self.last_used = datetime.utcnow()


@dataclass
class PluginHookEvent:
    """Event for plugin hook execution."""
    hook_name: str
    plugin_id: str
    context: Dict[str, Any]
    timestamp: datetime
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class PluginPermission:
    """Permission definition for plugins."""
    permission_id: str
    name: str
    description: str
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    required_for_hooks: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.required_for_hooks is None:
            self.required_for_hooks = []


class BasePluginManager(ABC):
    """Base class for plugin management systems."""
    
    def __init__(self):
        """Initialize the plugin manager."""
        self._registered_plugins: Dict[str, PluginMetadata] = {}
        self._active_instances: Dict[str, PluginInstance] = {}
        self._plugin_directories: List[str] = []
        self._hook_registry: Dict[str, List[str]] = {}
        self._permissions: Dict[str, PluginPermission] = {}
        self._plugin_permissions: Dict[str, List[str]] = {}
        self._auto_discovery_enabled = True
        self._permission_check_enabled = True
        self._max_plugins_per_type = 50
        self._plugin_timeout_seconds = 30
        self._framework_version = "1.0.0"
        
        # Initialize default permissions
        self._initialize_default_permissions()
    
    async def initialize(
        self,
        plugin_directories: List[str] = None,
        auto_discovery: bool = True
    ) -> bool:
        """
        Initialize the plugin manager.
        
        Args:
            plugin_directories: Directories to search for plugins
            auto_discovery: Enable automatic plugin discovery
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            if plugin_directories:
                self._plugin_directories = plugin_directories
            
            self._auto_discovery_enabled = auto_discovery
            
            # Auto-discover plugins if enabled
            if auto_discovery:
                await self._discover_plugins()
            
            # Register default hooks
            await self._register_default_hooks()
            
            print(f"PluginManager initialized with {len(self._registered_plugins)} plugins")
            return True
            
        except Exception as e:
            print(f"Failed to initialize PluginManager: {str(e)}")
            return False
    
    @abstractmethod
    async def load_plugin(self, plugin_id: str, **kwargs) -> Optional[str]:
        """
        Load a plugin.
        
        Args:
            plugin_id: Plugin identifier
            **kwargs: Plugin-specific arguments
            
        Returns:
            Instance ID if successful, None otherwise
        """
        pass
    
    @abstractmethod
    async def unload_plugin(self, instance_id: str) -> bool:
        """
        Unload a plugin instance.
        
        Args:
            instance_id: Instance ID to unload
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    async def register_plugin(self, metadata: PluginMetadata) -> bool:
        """
        Register a plugin metadata.
        
        Args:
            metadata: Plugin metadata
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            # Validate metadata
            if not await self._validate_plugin_metadata(metadata):
                return False
            
            # Check if already registered
            if metadata.plugin_id in self._registered_plugins:
                print(f"Plugin {metadata.plugin_id} already registered")
                return False
            
            # Check version compatibility
            if not await self._check_version_compatibility(metadata):
                return False
            
            # Check permissions
            if self._permission_check_enabled:
                if not await self._check_plugin_permissions(metadata):
                    print(f"Plugin {metadata.plugin_id} requires permissions that are not granted")
                    return False
            
            # Register plugin
            self._registered_plugins[metadata.plugin_id] = metadata
            
            # Store plugin permissions
            self._plugin_permissions[metadata.plugin_id] = metadata.permissions
            
            print(f"Registered plugin: {metadata.plugin_id}")
            return True
            
        except Exception as e:
            print(f"Failed to register plugin {metadata.plugin_id}: {str(e)}")
            return False
    
    async def execute_hook(
        self,
        hook_name: str,
        context: Dict[str, Any],
        timeout_ms: Optional[int] = None
    ) -> List[PluginHookEvent]:
        """
        Execute a hook across all registered plugins.
        
        Args:
            hook_name: Name of the hook to execute
            context: Hook execution context
            timeout_ms: Timeout in milliseconds
            
        Returns:
            List of hook execution events
        """
        try:
            events = []
            
            # Get plugins that have this hook
            plugin_ids = self._hook_registry.get(hook_name, [])
            
            for plugin_id in plugin_ids:
                instance = self._get_active_instance(plugin_id)
                if not instance:
                    continue
                
                # Check permissions
                if not await self._check_hook_permissions(plugin_id, hook_name):
                    continue
                
                # Execute hook
                event = await self._execute_plugin_hook(
                    instance,
                    hook_name,
                    context,
                    timeout_ms
                )
                
                if event:
                    events.append(event)
            
            return events
            
        except Exception as e:
            print(f"Error executing hook {hook_name}: {str(e)}")
            return []
    
    async def get_plugin_info(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a plugin.
        
        Args:
            plugin_id: Plugin ID
            
        Returns:
            Plugin information if found, None otherwise
        """
        metadata = self._registered_plugins.get(plugin_id)
        if not metadata:
            return None
        
        # Get active instances
        active_instances = [
            inst.instance_id for inst in self._active_instances.values()
            if inst.plugin_id == plugin_id and inst.is_active
        ]
        
        return {
            "plugin_id": plugin_id,
            "metadata": metadata.__dict__,
            "active_instances": active_instances,
            "permissions": self._plugin_permissions.get(plugin_id, []),
            "registered_at": datetime.utcnow().isoformat()
        }
    
    async def list_plugins(self) -> List[str]:
        """
        List all registered plugin IDs.
        
        Returns:
            List of plugin IDs
        """
        return list(self._registered_plugins.keys())
    
    async def list_instances(self) -> List[str]:
        """
        List all active instance IDs.
        
        Returns:
            List of instance IDs
        """
        return [inst_id for inst_id, inst in self._active_instances.items() if inst.is_active]
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get plugin manager statistics.
        
        Returns:
            Statistics dictionary
        """
        total_instances = len(self._active_instances)
        active_instances = sum(1 for inst in self._active_instances.values() if inst.is_active)
        
        plugin_stats = {}
        for plugin_id in self._registered_plugins:
            plugin_instances = [
                inst for inst in self._active_instances.values()
                if inst.plugin_id == plugin_id and inst.is_active
            ]
            plugin_stats[plugin_id] = {
                "active_instances": len(plugin_instances),
                "total_executions": sum(inst.execution_count for inst in plugin_instances),
                "error_count": sum(inst.error_count for inst in plugin_instances),
                "last_used": max((inst.last_used for inst in plugin_instances), default=None)
            }
        
        return {
            "registered_plugins": len(self._registered_plugins),
            "total_instances": total_instances,
            "active_instances": active_instances,
            "plugin_stats": plugin_stats,
            "hook_registry": {hook: len(plugins) for hook, plugins in self._hook_registry.items()},
            "permissions_granted": len(self._permissions),
            "auto_discovery_enabled": self._auto_discovery_enabled,
            "framework_version": self._framework_version
        }
    
    async def _discover_plugins(self) -> None:
        """Auto-discover plugins from configured directories."""
        for plugin_dir in self._plugin_directories:
            try:
                path = Path(plugin_dir)
                if not path.exists():
                    continue
                
                # Look for plugin files
                for plugin_file in path.rglob("*.py"):
                    if plugin_file.name.startswith("__"):
                        continue
                    
                    await self._inspect_plugin_file(plugin_file)
                    
            except Exception as e:
                print(f"Error discovering plugins in {plugin_dir}: {str(e)}")
    
    async def _inspect_plugin_file(self, file_path: Path) -> None:
        """Inspect a Python file for plugins."""
        try:
            # Convert path to module name
            relative_path = file_path.relative_to(Path.cwd())
            module_name = str(relative_path.with_suffix("")).replace("/", ".").replace("\\", ".")
            
            # Import module
            module = importlib.import_module(module_name)
            
            # Look for plugin classes
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if self._is_plugin_class(obj, module):
                    await self._register_plugin_from_class(obj)
                    
        except Exception as e:
            print(f"Error inspecting plugin file {file_path}: {str(e)}")
    
    def _is_plugin_class(self, cls: Any, module: Any) -> bool:
        """Check if a class is a plugin."""
        # Check if it has plugin metadata
        if hasattr(cls, 'PLUGIN_METADATA'):
            return True
        
        # Check if it has required plugin methods
        required_methods = ['initialize', 'cleanup']
        for method in required_methods:
            if not hasattr(cls, method):
                return False
        
        return True
    
    async def _register_plugin_from_class(self, plugin_class: type) -> None:
        """Register a plugin from its class."""
        try:
            # Get plugin metadata
            if hasattr(plugin_class, 'PLUGIN_METADATA'):
                metadata_dict = plugin_class.PLUGIN_METADATA
                metadata = PluginMetadata(**metadata_dict)
            else:
                # Create default metadata
                metadata = PluginMetadata(
                    plugin_id=plugin_class.__name__.lower(),
                    name=plugin_class.__name__,
                    version="1.0.0",
                    description=f"Plugin class {plugin_class.__name__}"
                )
            
            await self.register_plugin(metadata)
            
        except Exception as e:
            print(f"Failed to register plugin class {plugin_class.__name__}: {str(e)}")
    
    async def _validate_plugin_metadata(self, metadata: PluginMetadata) -> bool:
        """Validate plugin metadata."""
        try:
            # Check required fields
            if not metadata.plugin_id or not metadata.name or not metadata.version:
                return False
            
            # Check entry point
            if not metadata.entry_point:
                return False
            
            # Check hooks
            valid_hooks = ['pre_scrape', 'post_scrape', 'pre_process', 'post_process']
            for hook in metadata.hooks:
                if hook not in valid_hooks:
                    return False
            
            return True
            
        except Exception:
            return False
    
    async def _check_version_compatibility(self, metadata: PluginMetadata) -> bool:
        """Check plugin version compatibility."""
        try:
            # Simple version comparison (can be enhanced with semantic versioning)
            framework_version = self._framework_version
            min_version = metadata.min_framework_version
            max_version = metadata.max_framework_version
            
            # For now, just check if versions match
            return framework_version == min_version or framework_version == max_version
            
        except Exception:
            return False
    
    async def _check_plugin_permissions(self, metadata: PluginMetadata) -> bool:
        """Check if plugin permissions are available."""
        try:
            for permission in metadata.permissions:
                if permission not in self._permissions:
                    print(f"Plugin requires permission '{permission}' which is not defined")
                    return False
            
            return True
            
        except Exception:
            return False
    
    async def _check_hook_permissions(self, plugin_id: str, hook_name: str) -> bool:
        """Check if plugin has required permissions for a hook."""
        try:
            plugin_permissions = self._plugin_permissions.get(plugin_id, [])
            
            for permission in self._permissions.values():
                if hook_name in permission.required_for_hooks:
                    if permission.permission_id not in plugin_permissions:
                        return False
            
            return True
            
        except Exception:
            return False
    
    def _get_active_instance(self, plugin_id: str) -> Optional[PluginInstance]:
        """Get an active instance of a plugin."""
        for instance in self._active_instances.values():
            if instance.plugin_id == plugin_id and instance.is_active:
                instance.last_used = datetime.utcnow()
                return instance
        return None
    
    async def _execute_plugin_hook(
        self,
        instance: PluginInstance,
        hook_name: str,
        context: Dict[str, Any],
        timeout_ms: Optional[int]
    ) -> Optional[PluginHookEvent]:
        """Execute a hook on a specific plugin instance."""
        try:
            start_time = datetime.utcnow()
            
            # Check if plugin has the hook method
            if not hasattr(instance.instance, hook_name):
                return None
            
            hook_method = getattr(instance.instance, hook_name)
            
            # Execute with timeout
            timeout = timeout_ms / 1000.0 if timeout_ms else self._plugin_timeout_seconds
            
            try:
                if inspect.iscoroutinefunction(hook_method):
                    result = await asyncio.wait_for(hook_method(context), timeout=timeout)
                else:
                    result = hook_method(context)
                
                end_time = datetime.utcnow()
                execution_time = (end_time - start_time).total_seconds() * 1000
                
                # Update instance stats
                instance.last_used = datetime.utcnow()
                instance.execution_count += 1
                
                return PluginHookEvent(
                    hook_name=hook_name,
                    plugin_id=instance.plugin_id,
                    context=context,
                    timestamp=start_time,
                    result=result,
                    execution_time_ms=execution_time
                )
                
            except asyncio.TimeoutError:
                instance.error_count += 1
                instance.last_error = f"Hook {hook_name} timed out"
                
                return PluginHookEvent(
                    hook_name=hook_name,
                    plugin_id=instance.plugin_id,
                    context=context,
                    timestamp=start_time,
                    error=f"Hook execution timed out after {timeout}s"
                )
                
            except Exception as e:
                instance.error_count += 1
                instance.last_error = str(e)
                
                return PluginHookEvent(
                    hook_name=hook_name,
                    plugin_id=instance.plugin_id,
                    context=context,
                    timestamp=start_time,
                    error=str(e)
                )
                
        except Exception as e:
            print(f"Error executing hook {hook_name} on plugin {instance.plugin_id}: {str(e)}")
            return None
    
    async def _register_default_hooks(self) -> None:
        """Register default hook types."""
        default_hooks = [
            'pre_scrape',
            'post_scrape',
            'pre_process',
            'post_process',
            'pre_navigation',
            'post_navigation',
            'validation_failed',
            'error_occurred'
        ]
        
        for hook in default_hooks:
            self._hook_registry[hook] = []
    
    def _initialize_default_permissions(self) -> None:
        """Initialize default permissions."""
        default_permissions = [
            PluginPermission(
                permission_id="read_data",
                name="Read Data",
                description="Permission to read scraped data",
                risk_level="LOW"
            ),
            PluginPermission(
                permission_id="write_data",
                name="Write Data",
                description="Permission to modify scraped data",
                risk_level="MEDIUM"
            ),
            PluginPermission(
                permission_id="access_network",
                name="Access Network",
                description="Permission to make network requests",
                risk_level="HIGH",
                required_for_hooks=["pre_scrape", "post_scrape"]
            ),
            PluginPermission(
                permission_id="modify_browser",
                name="Modify Browser",
                description="Permission to modify browser state",
                risk_level="CRITICAL",
                required_for_hooks=["pre_navigation", "post_navigation"]
            )
        ]
        
        for permission in default_permissions:
            self._permissions[permission.permission_id] = permission
    
    async def cleanup(self) -> None:
        """Clean up plugin manager resources."""
        try:
            # Unload all active instances
            instances_to_unload = list(self._active_instances.keys())
            for instance_id in instances_to_unload:
                await self.unload_plugin(instance_id)
            
            # Clear registries
            self._registered_plugins.clear()
            self._active_instances.clear()
            self._hook_registry.clear()
            self._permissions.clear()
            self._plugin_permissions.clear()
            
            print("PluginManager cleanup completed")
            
        except Exception as e:
            print(f"Error during PluginManager cleanup: {str(e)}")


class PluginManagerError(Exception):
    """Exception raised when plugin manager operations fail."""
    pass


class PluginNotFoundError(PluginManagerError):
    """Exception raised when a plugin is not found."""
    pass


class PluginLoadError(PluginManagerError):
    """Exception raised when plugin loading fails."""
    pass


class PermissionDeniedError(PluginManagerError):
    """Exception raised when plugin permissions are denied."""
    pass
