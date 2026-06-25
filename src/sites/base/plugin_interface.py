"""
Plugin base interface for the scraper framework.

This module provides the core plugin interface and base classes that all plugins
must implement, including lifecycle hooks, metadata, and plugin registration.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, Callable, Type
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import inspect
import uuid

from .component_interface import ComponentContext, ComponentResult


class PluginStatus(Enum):
    """Plugin status enumeration."""
    INACTIVE = "inactive"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"
    LOADING = "loading"
    UNLOADING = "unloading"


class PluginType(Enum):
    """Plugin type enumeration."""
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    EXTRACTION = "extraction"
    MONITORING = "monitoring"
    AUTHENTICATION = "authentication"
    RATE_LIMITING = "rate_limiting"
    STEALTH = "stealth"
    STORAGE = "storage"
    NOTIFICATION = "notification"
    CUSTOM = "custom"


class HookType(Enum):
    """Hook type enumeration."""
    BEFORE_SCRAPE = "before_scrape"
    AFTER_SCRAPE = "after_scrape"
    BEFORE_EXTRACT = "before_extract"
    AFTER_EXTRACT = "after_extract"
    BEFORE_NAVIGATE = "before_navigate"
    AFTER_NAVIGATE = "after_navigate"
    BEFORE_CLICK = "before_click"
    AFTER_CLICK = "after_click"
    BEFORE_TYPE = "before_type"
    AFTER_TYPE = "after_type"
    ERROR_OCCURRED = "error_occurred"
    VALIDATION_FAILED = "validation_failed"
    COMPONENT_LOADED = "component_loaded"
    COMPONENT_UNLOADED = "component_unloaded"


@dataclass
class PluginMetadata:
    """Plugin metadata."""
    id: str
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    status: PluginStatus = PluginStatus.INACTIVE
    dependencies: List[str] = field(default_factory=list)
    min_framework_version: str = "1.0.0"
    max_framework_version: Optional[str] = None
    permissions: List[str] = field(default_factory=list)
    configuration_schema: Optional[Dict[str, Any]] = None
    hooks: List[HookType] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)
    homepage: Optional[str] = None
    repository: Optional[str] = None
    license: str = "MIT"
    
    def __post_init__(self):
        """Post-initialization validation."""
        if not self.id:
            raise ValueError("Plugin ID is required")
        if not self.name:
            raise ValueError("Plugin name is required")
        if not self.version:
            raise ValueError("Plugin version is required")
        if not self.author:
            raise ValueError("Plugin author is required")


@dataclass
class PluginContext:
    """Plugin execution context."""
    plugin_id: str
    plugin_metadata: PluginMetadata
    framework_context: ComponentContext
    configuration: Dict[str, Any] = field(default_factory=dict)
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_time: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginResult:
    """Plugin execution result."""
    success: bool
    plugin_id: str
    hook_type: Optional[HookType] = None
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class PluginHook:
    """Plugin hook definition."""
    
    def __init__(self, hook_type: HookType, callback: Callable, 
                 priority: int = 0, condition: Optional[Callable] = None):
        self.hook_type = hook_type
        self.callback = callback
        self.priority = priority
        self.condition = condition
        self.plugin_id = None
        self.execution_count = 0
        self.last_execution = None
        self.total_execution_time_ms = 0.0
    
    async def execute(self, context: PluginContext, **kwargs) -> PluginResult:
        """Execute the hook."""
        start_time = datetime.utcnow()
        
        try:
            # Check condition if provided
            if self.condition and not self.condition(context, **kwargs):
                return PluginResult(
                    success=True,
                    plugin_id=self.plugin_id,
                    hook_type=self.hook_type,
                    data={"skipped": True, "reason": "condition_not_met"}
                )
            
            # Execute callback
            if inspect.iscoroutinefunction(self.callback):
                result = await self.callback(context, **kwargs)
            else:
                result = self.callback(context, **kwargs)
            
            # Update statistics
            self.execution_count += 1
            self.last_execution = datetime.utcnow()
            
            execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.total_execution_time_ms += execution_time_ms
            
            # Convert result to PluginResult if needed
            if isinstance(result, PluginResult):
                result.execution_time_ms = execution_time_ms
                return result
            elif isinstance(result, dict):
                return PluginResult(
                    success=True,
                    plugin_id=self.plugin_id,
                    hook_type=self.hook_type,
                    data=result,
                    execution_time_ms=execution_time_ms
                )
            elif isinstance(result, bool):
                return PluginResult(
                    success=result,
                    plugin_id=self.plugin_id,
                    hook_type=self.hook_type,
                    execution_time_ms=execution_time_ms
                )
            else:
                return PluginResult(
                    success=True,
                    plugin_id=self.plugin_id,
                    hook_type=self.hook_type,
                    data={"result": result},
                    execution_time_ms=execution_time_ms
                )
                
        except Exception as e:
            execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return PluginResult(
                success=False,
                plugin_id=self.plugin_id,
                hook_type=self.hook_type,
                errors=[str(e)],
                execution_time_ms=execution_time_ms
            )


class IPlugin(ABC):
    """Base plugin interface that all plugins must implement."""
    
    def __init__(self):
        """Initialize plugin."""
        self._metadata = None
        self._context = None
        self._hooks = []
        self._status = PluginStatus.INACTIVE
        self._initialized = False
    
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        pass
    
    @abstractmethod
    async def initialize(self, context: PluginContext) -> bool:
        """Initialize the plugin."""
        pass
    
    @abstractmethod
    async def execute(self, context: PluginContext, hook_type: HookType, **kwargs) -> PluginResult:
        """Execute the plugin for a specific hook."""
        pass
    
    @abstractmethod
    async def cleanup(self, context: PluginContext) -> bool:
        """Clean up plugin resources."""
        pass
    
    @abstractmethod
    async def validate_configuration(self, configuration: Dict[str, Any]) -> bool:
        """Validate plugin configuration."""
        pass
    
    def get_status(self) -> PluginStatus:
        """Get plugin status."""
        return self._status
    
    def is_initialized(self) -> bool:
        """Check if plugin is initialized."""
        return self._initialized
    
    def get_hooks(self) -> List[PluginHook]:
        """Get all hooks registered by this plugin."""
        return self._hooks.copy()
    
    def add_hook(self, hook_type: HookType, callback: Callable, 
                priority: int = 0, condition: Optional[Callable] = None) -> None:
        """Add a hook to the plugin."""
        hook = PluginHook(hook_type, callback, priority, condition)
        hook.plugin_id = self.metadata.id
        self._hooks.append(hook)
    
    def remove_hook(self, hook_type: HookType, callback: Callable) -> bool:
        """Remove a hook from the plugin."""
        for i, hook in enumerate(self._hooks):
            if hook.hook_type == hook_type and hook.callback == callback:
                del self._hooks[i]
                return True
        return False
    
    def get_hook_statistics(self) -> Dict[str, Any]:
        """Get hook execution statistics."""
        stats = {}
        
        for hook in self._hooks:
            stats[f"{hook.hook_type.value}_{id(hook.callback)}"] = {
                'execution_count': hook.execution_count,
                'last_execution': hook.last_execution.isoformat() if hook.last_execution else None,
                'total_execution_time_ms': hook.total_execution_time_ms,
                'average_execution_time_ms': (
                    hook.total_execution_time_ms / hook.execution_count
                    if hook.execution_count > 0 else 0
                )
            }
        
        return stats


class BasePlugin(IPlugin):
    """Base plugin implementation with common functionality."""
    
    def __init__(self):
        """Initialize base plugin."""
        super().__init__()
        self._logger = None
        self._config = {}
        self._telemetry = {
            'initialization_time_ms': 0,
            'execution_count': 0,
            'total_execution_time_ms': 0,
            'error_count': 0,
            'last_execution': None
        }
    
    async def initialize(self, context: PluginContext) -> bool:
        """Initialize the plugin."""
        start_time = datetime.utcnow()
        
        try:
            self._context = context
            self._config = context.configuration
            
            # Set up logger
            self._setup_logger(context)
            
            # Validate configuration
            if not await self.validate_configuration(self._config):
                self._status = PluginStatus.ERROR
                return False
            
            # Perform plugin-specific initialization
            init_success = await self._on_initialize(context)
            
            if init_success:
                self._status = PluginStatus.ACTIVE
                self._initialized = True
                
                # Register hooks
                await self._register_hooks()
                
                self._logger.info(f"Plugin {self.metadata.id} initialized successfully")
            else:
                self._status = PluginStatus.ERROR
                self._logger.error(f"Plugin {self.metadata.id} initialization failed")
            
            # Update telemetry
            init_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._telemetry['initialization_time_ms'] = init_time_ms
            
            return init_success
            
        except Exception as e:
            self._status = PluginStatus.ERROR
            if self._logger:
                self._logger.error(f"Plugin initialization error: {str(e)}")
            return False
    
    async def execute(self, context: PluginContext, hook_type: HookType, **kwargs) -> PluginResult:
        """Execute the plugin for a specific hook."""
        start_time = datetime.utcnow()
        
        try:
            # Check if plugin is active
            if self._status != PluginStatus.ACTIVE:
                return PluginResult(
                    success=False,
                    plugin_id=self.metadata.id,
                    hook_type=hook_type,
                    errors=[f"Plugin is not active: {self._status.value}"]
                )
            
            # Check if hook is supported
            if hook_type not in self.metadata.hooks:
                return PluginResult(
                    success=True,
                    plugin_id=self.metadata.id,
                    hook_type=hook_type,
                    data={"skipped": True, "reason": "hook_not_supported"}
                )
            
            # Update telemetry
            self._telemetry['execution_count'] += 1
            
            # Execute plugin-specific logic
            result = await self._on_execute(context, hook_type, **kwargs)
            
            # Update telemetry
            execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._telemetry['total_execution_time_ms'] += execution_time_ms
            self._telemetry['last_execution'] = datetime.utcnow()
            
            if not result.success:
                self._telemetry['error_count'] += 1
            
            return result
            
        except Exception as e:
            # Update telemetry
            self._telemetry['error_count'] += 1
            execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            if self._logger:
                self._logger.error(f"Plugin execution error: {str(e)}")
            
            return PluginResult(
                success=False,
                plugin_id=self.metadata.id,
                hook_type=hook_type,
                errors=[str(e)],
                execution_time_ms=execution_time_ms
            )
    
    async def cleanup(self, context: PluginContext) -> bool:
        """Clean up plugin resources."""
        try:
            # Perform plugin-specific cleanup
            cleanup_success = await self._on_cleanup(context)
            
            # Clear hooks
            self._hooks.clear()
            
            # Update status
            self._status = PluginStatus.INACTIVE
            self._initialized = False
            
            if self._logger:
                self._logger.info(f"Plugin {self.metadata.id} cleaned up successfully")
            
            return cleanup_success
            
        except Exception as e:
            if self._logger:
                self._logger.error(f"Plugin cleanup error: {str(e)}")
            return False
    
    async def validate_configuration(self, configuration: Dict[str, Any]) -> bool:
        """Validate plugin configuration."""
        try:
            # Use schema if available
            if self.metadata.configuration_schema:
                return self._validate_with_schema(configuration)
            
            # Default validation
            return await self._on_validate_configuration(configuration)
            
        except Exception as e:
            if self._logger:
                self._logger.error(f"Configuration validation error: {str(e)}")
            return False
    
    def _setup_logger(self, context: PluginContext) -> None:
        """Set up plugin logger."""
        # Use framework context logger
        if hasattr(context.framework_context, 'logger'):
            self._logger = context.framework_context.logger
        else:
            # Create basic logger
            import logging
            self._logger = logging.getLogger(f"plugin.{self.metadata.id}")
    
    def _validate_with_schema(self, configuration: Dict[str, Any]) -> bool:
        """Validate configuration using JSON schema."""
        try:
            import jsonschema
            
            schema = self.metadata.configuration_schema
            jsonschema.validate(configuration, schema)
            return True
            
        except ImportError:
            # jsonschema not available, skip validation
            return True
        except Exception as e:
            if self._logger:
                self._logger.error(f"Schema validation error: {str(e)}")
            return False
    
    async def _on_initialize(self, context: PluginContext) -> bool:
        """Override to implement plugin-specific initialization."""
        return True
    
    async def _on_execute(self, context: PluginContext, hook_type: HookType, **kwargs) -> PluginResult:
        """Override to implement plugin-specific execution logic."""
        return PluginResult(
            success=True,
            plugin_id=self.metadata.id,
            hook_type=hook_type
        )
    
    async def _on_cleanup(self, context: PluginContext) -> bool:
        """Override to implement plugin-specific cleanup."""
        return True
    
    async def _on_validate_configuration(self, configuration: Dict[str, Any]) -> bool:
        """Override to implement plugin-specific configuration validation."""
        return True
    
    async def _register_hooks(self) -> None:
        """Override to register plugin hooks."""
        pass
    
    def get_telemetry(self) -> Dict[str, Any]:
        """Get plugin telemetry data."""
        telemetry = self._telemetry.copy()
        telemetry.update({
            'plugin_id': self.metadata.id,
            'plugin_name': self.metadata.name,
            'plugin_version': self.metadata.version,
            'plugin_type': self.metadata.plugin_type.value,
            'status': self._status.value,
            'initialized': self._initialized,
            'hook_count': len(self._hooks),
            'hook_statistics': self.get_hook_statistics()
        })
        
        return telemetry


class PluginRegistry:
    """Plugin registry for managing plugin instances."""
    
    def __init__(self):
        """Initialize plugin registry."""
        self._plugins: Dict[str, IPlugin] = {}
        self._plugin_classes: Dict[str, Type[IPlugin]] = {}
        self._metadata: Dict[str, PluginMetadata] = {}
        self._hooks: Dict[HookType, List[PluginHook]] = {}
    
    def register_plugin_class(self, plugin_class: Type[IPlugin]) -> None:
        """Register a plugin class."""
        # Create temporary instance to get metadata
        temp_instance = plugin_class()
        metadata = temp_instance.metadata
        
        self._plugin_classes[metadata.id] = plugin_class
        self._metadata[metadata.id] = metadata
    
    def create_plugin(self, plugin_id: str) -> Optional[IPlugin]:
        """Create a plugin instance."""
        if plugin_id not in self._plugin_classes:
            return None
        
        plugin_class = self._plugin_classes[plugin_id]
        return plugin_class()
    
    def register_plugin(self, plugin: IPlugin) -> bool:
        """Register a plugin instance."""
        metadata = plugin.metadata
        
        if metadata.id in self._plugins:
            return False
        
        self._plugins[metadata.id] = plugin
        self._metadata[metadata.id] = metadata
        
        # Register hooks
        for hook in plugin.get_hooks():
            if hook.hook_type not in self._hooks:
                self._hooks[hook.hook_type] = []
            self._hooks[hook.hook_type].append(hook)
            # Sort by priority
            self._hooks[hook.hook_type].sort(key=lambda h: h.priority, reverse=True)
        
        return True
    
    def unregister_plugin(self, plugin_id: str) -> bool:
        """Unregister a plugin."""
        if plugin_id not in self._plugins:
            return False
        
        plugin = self._plugins[plugin_id]
        
        # Remove hooks
        for hook in plugin.get_hooks():
            if hook.hook_type in self._hooks:
                self._hooks[hook.hook_type] = [
                    h for h in self._hooks[hook.hook_type]
                    if h.plugin_id != plugin_id
                ]
        
        # Remove plugin
        del self._plugins[plugin_id]
        del self._metadata[plugin_id]
        
        return True
    
    def get_plugin(self, plugin_id: str) -> Optional[IPlugin]:
        """Get a plugin instance."""
        return self._plugins.get(plugin_id)
    
    def get_plugins(self) -> Dict[str, IPlugin]:
        """Get all plugin instances."""
        return self._plugins.copy()
    
    def get_plugin_metadata(self, plugin_id: str) -> Optional[PluginMetadata]:
        """Get plugin metadata."""
        return self._metadata.get(plugin_id)
    
    def get_all_metadata(self) -> Dict[str, PluginMetadata]:
        """Get all plugin metadata."""
        return self._metadata.copy()
    
    def get_plugins_by_type(self, plugin_type: PluginType) -> List[IPlugin]:
        """Get plugins by type."""
        return [
            plugin for plugin in self._plugins.values()
            if plugin.metadata.plugin_type == plugin_type
        ]
    
    def get_plugins_by_hook(self, hook_type: HookType) -> List[IPlugin]:
        """Get plugins that support a specific hook."""
        return [
            plugin for plugin in self._plugins.values()
            if hook_type in plugin.metadata.hooks
        ]
    
    def get_hooks(self, hook_type: HookType) -> List[PluginHook]:
        """Get hooks for a specific hook type."""
        return self._hooks.get(hook_type, []).copy()
    
    def get_plugin_count(self) -> int:
        """Get total plugin count."""
        return len(self._plugins)
    
    def get_plugin_count_by_status(self, status: PluginStatus) -> int:
        """Get plugin count by status."""
        return len([
            plugin for plugin in self._plugins.values()
            if plugin.get_status() == status
        ])


# Global plugin registry
_plugin_registry = PluginRegistry()


# Convenience functions
def register_plugin_class(plugin_class: Type[IPlugin]) -> None:
    """Register a plugin class."""
    _plugin_registry.register_plugin_class(plugin_class)


def register_plugin(plugin: IPlugin) -> bool:
    """Register a plugin instance."""
    return _plugin_registry.register_plugin(plugin)


def get_plugin(plugin_id: str) -> Optional[IPlugin]:
    """Get a plugin instance."""
    return _plugin_registry.get_plugin(plugin_id)


def get_plugins() -> Dict[str, IPlugin]:
    """Get all plugin instances."""
    return _plugin_registry.get_plugins()


def get_plugin_metadata(plugin_id: str) -> Optional[PluginMetadata]:
    """Get plugin metadata."""
    return _plugin_registry.get_plugin_metadata(plugin_id)


def get_all_metadata() -> Dict[str, PluginMetadata]:
    """Get all plugin metadata."""
    return _plugin_registry.get_all_metadata()


def get_plugins_by_type(plugin_type: PluginType) -> List[IPlugin]:
    """Get plugins by type."""
    return _plugin_registry.get_plugins_by_type(plugin_type)


def get_hooks(hook_type: HookType) -> List[PluginHook]:
    """Get hooks for a specific hook type."""
    return _plugin_registry.get_hooks(hook_type)


def get_plugin_registry() -> PluginRegistry:
    """Get the global plugin registry."""
    return _plugin_registry
