"""
Plugin lifecycle manager for the scraper framework.

This module provides comprehensive plugin lifecycle management, including
initialization, execution, cleanup, and state management.
"""

import asyncio
import threading
import time
from typing import Dict, Any, List, Optional, Callable, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future
import weakref

from .plugin_interface import (
    IPlugin, PluginContext, PluginResult, PluginStatus, HookType,
    PluginMetadata, get_plugin_registry
)
from .plugin_error_handling import PluginErrorHandler, PluginError, ErrorSeverity


class LifecycleEvent(Enum):
    """Plugin lifecycle event enumeration."""
    DISCOVERED = "discovered"
    REGISTERED = "registered"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    ACTIVATING = "activating"
    ACTIVATED = "activated"
    DEACTIVATING = "deactivating"
    DEACTIVATED = "deactivated"
    CLEANING_UP = "cleaning_up"
    CLEANED_UP = "cleaned_up"
    ERROR_OCCURRED = "error_occurred"
    UNREGISTERED = "unregistered"


@dataclass
class LifecycleEventRecord:
    """Plugin lifecycle event record."""
    plugin_id: str
    event: LifecycleEvent
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    error: Optional[str] = None


@dataclass
class PluginLifecycleState:
    """Plugin lifecycle state."""
    plugin_id: str
    status: PluginStatus
    initialized: bool = False
    active: bool = False
    error_count: int = 0
    last_error: Optional[str] = None
    last_activity: Optional[datetime] = None
    initialization_time: Optional[datetime] = None
    activation_time: Optional[datetime] = None
    total_execution_time_ms: float = 0.0
    execution_count: int = 0
    events: List[LifecycleEventRecord] = field(default_factory=list)


class PluginLifecycleManager:
    """Plugin lifecycle manager."""
    
    def __init__(self, error_handler: Optional[PluginErrorHandler] = None):
        """Initialize plugin lifecycle manager."""
        self.error_handler = error_handler or PluginErrorHandler()
        self.registry = get_plugin_registry()
        
        # Plugin state management
        self._plugin_states: Dict[str, PluginLifecycleState] = {}
        self._plugin_instances: Dict[str, IPlugin] = {}
        self._plugin_contexts: Dict[str, PluginContext] = {}
        
        # Lifecycle management
        self._initialization_lock = threading.RLock()
        self._execution_lock = threading.RLock()
        self._cleanup_lock = threading.RLock()
        
        # Event handling
        self._event_listeners: Dict[LifecycleEvent, List[Callable]] = {}
        self._event_history: List[LifecycleEventRecord] = []
        
        # Execution management
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._running_executions: Dict[str, Future] = {}
        
        # Configuration
        self._auto_cleanup = True
        self._max_execution_time_seconds = 300
        self._max_error_count = 5
        self._error_backoff_seconds = 60
        self._health_check_interval = timedelta(minutes=5)
        
        # Statistics
        self._stats = {
            'total_plugins': 0,
            'active_plugins': 0,
            'error_plugins': 0,
            'total_executions': 0,
            'total_execution_time_ms': 0.0,
            'average_execution_time_ms': 0.0,
            'total_errors': 0
        }
        
        # Background tasks
        self._health_check_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Weak references for cleanup
        self._weak_refs: Dict[str, weakref.ref] = {}
    
    async def initialize_plugin(self, plugin_id: str, context: PluginContext) -> bool:
        """
        Initialize a plugin.
        
        Args:
            plugin_id: Plugin ID
            context: Plugin context
            
        Returns:
            True if initialization successful
        """
        start_time = datetime.utcnow()
        
        async with self._initialization_lock:
            try:
                # Check if plugin exists
                plugin = self.registry.get_plugin(plugin_id)
                if not plugin:
                    await self._emit_event(LifecycleEvent.ERROR_OCCURRED, plugin_id, {
                        'error': f'Plugin {plugin_id} not found in registry'
                    })
                    return False
                
                # Check current state
                state = self._get_or_create_state(plugin_id)
                if state.status == PluginStatus.INITIALIZED:
                    return True
                
                if state.status == PluginStatus.ERROR:
                    # Check if enough time has passed for retry
                    if state.last_error:
                        time_since_error = datetime.utcnow() - state.last_activity
                        if time_since_error < timedelta(seconds=self._error_backoff_seconds):
                            return False
                
                # Update state
                state.status = PluginStatus.INITIALIZING
                await self._emit_event(LifecycleEvent.INITIALIZING, plugin_id)
                
                # Initialize plugin
                init_success = await plugin.initialize(context)
                
                if init_success:
                    # Store plugin instance and context
                    self._plugin_instances[plugin_id] = plugin
                    self._plugin_contexts[plugin_id] = context
                    self._weak_refs[plugin_id] = weakref.ref(plugin)
                    
                    # Update state
                    state.status = PluginStatus.INITIALIZED
                    state.initialized = True
                    state.initialization_time = datetime.utcnow()
                    state.last_activity = datetime.utcnow()
                    state.error_count = 0
                    state.last_error = None
                    
                    await self._emit_event(LifecycleEvent.INITIALIZED, plugin_id, {
                        'initialization_time_ms': (datetime.utcnow() - start_time).total_seconds() * 1000
                    })
                    
                    return True
                else:
                    # Handle initialization failure
                    state.status = PluginStatus.ERROR
                    state.error_count += 1
                    state.last_error = "Initialization failed"
                    state.last_activity = datetime.utcnow()
                    
                    await self._emit_event(LifecycleEvent.ERROR_OCCURRED, plugin_id, {
                        'error': 'Initialization failed',
                        'error_count': state.error_count
                    })
                    
                    return False
                    
            except Exception as e:
                # Handle unexpected errors
                state = self._get_or_create_state(plugin_id)
                state.status = PluginStatus.ERROR
                state.error_count += 1
                state.last_error = str(e)
                state.last_activity = datetime.utcnow()
                
                await self._emit_event(LifecycleEvent.ERROR_OCCURRED, plugin_id, {
                    'error': str(e),
                    'error_count': state.error_count
                })
                
                await self.error_handler.handle_error(
                    PluginError(
                        plugin_id=plugin_id,
                        error_type="initialization_error",
                        message=str(e),
                        severity=ErrorSeverity.HIGH
                    )
                )
                
                return False
    
    async def activate_plugin(self, plugin_id: str) -> bool:
        """
        Activate a plugin.
        
        Args:
            plugin_id: Plugin ID
            
        Returns:
            True if activation successful
        """
        start_time = datetime.utcnow()
        
        try:
            # Check if plugin is initialized
            state = self._get_or_create_state(plugin_id)
            if not state.initialized:
                await self._emit_event(LifecycleEvent.ERROR_OCCURRED, plugin_id, {
                    'error': 'Plugin not initialized'
                })
                return False
            
            if state.status == PluginStatus.ACTIVE:
                return True
            
            if state.status == PluginStatus.ERROR:
                # Check if plugin can be reactivated
                if state.error_count >= self._max_error_count:
                    return False
            
            # Update state
            state.status = PluginStatus.ACTIVATING
            await self._emit_event(LifecycleEvent.ACTIVATING, plugin_id)
            
            # Get plugin instance
            plugin = self._plugin_instances.get(plugin_id)
            if not plugin:
                await self._emit_event(LifecycleEvent.ERROR_OCCURRED, plugin_id, {
                    'error': 'Plugin instance not found'
                })
                return False
            
            # Get plugin context
            context = self._plugin_contexts.get(plugin_id)
            if not context:
                await self._emit_event(LifecycleEvent.ERROR_OCCURRED, plugin_id, {
                    'error': 'Plugin context not found'
                })
                return False
            
            # Activate plugin
            activation_success = await self._on_activate_plugin(plugin, context)
            
            if activation_success:
                # Update state
                state.status = PluginStatus.ACTIVE
                state.active = True
                state.activation_time = datetime.utcnow()
                state.last_activity = datetime.utcnow()
                
                await self._emit_event(LifecycleEvent.ACTIVATED, plugin_id, {
                    'activation_time_ms': (datetime.utcnow() - start_time).total_seconds() * 1000
                })
                
                # Update statistics
                self._update_stats()
                
                return True
            else:
                # Handle activation failure
                state.status = PluginStatus.ERROR
                state.error_count += 1
                state.last_error = "Activation failed"
                state.last_activity = datetime.utcnow()
                
                await self._emit_event(LifecycleEvent.ERROR_OCCURRED, plugin_id, {
                    'error': 'Activation failed',
                    'error_count': state.error_count
                })
                
                return False
                
        except Exception as e:
            # Handle unexpected errors
            state = self._get_or_create_state(plugin_id)
            state.status = PluginStatus.ERROR
            state.error_count += 1
            state.last_error = str(e)
            state.last_activity = datetime.utcnow()
            
            await self._emit_event(LifecycleEvent.ERROR_OCCURRED, plugin_id, {
                'error': str(e),
                'error_count': state.error_count
            })
            
            await self.error_handler.handle_error(
                PluginError(
                    plugin_id=plugin_id,
                    error_type="activation_error",
                    message=str(e),
                    severity=ErrorSeverity.HIGH
                )
            )
            
            return False
    
    async def deactivate_plugin(self, plugin_id: str) -> bool:
        """
        Deactivate a plugin.
        
        Args:
            plugin_id: Plugin ID
            
        Returns:
            True if deactivation successful
        """
        start_time = datetime.utcnow()
        
        try:
            # Check if plugin is active
            state = self._get_or_create_state(plugin_id)
            if not state.active:
                return True
            
            # Update state
            state.status = PluginStatus.DEACTIVATING
            await self._emit_event(LifecycleEvent.DEACTIVATING, plugin_id)
            
            # Get plugin instance
            plugin = self._plugin_instances.get(plugin_id)
            if not plugin:
                await self._emit_event(LifecycleEvent.ERROR_OCCURRED, plugin_id, {
                    'error': 'Plugin instance not found'
                })
                return False
            
            # Get plugin context
            context = self._plugin_contexts.get(plugin_id)
            if not context:
                await self._emit_event(LifecycleEvent.ERROR_OCCURRED, plugin_id, {
                    'error': 'Plugin context not found'
                })
                return False
            
            # Cancel running executions
            await self._cancel_plugin_executions(plugin_id)
            
            # Deactivate plugin
            deactivation_success = await self._on_deactivate_plugin(plugin, context)
            
            if deactivation_success:
                # Update state
                state.status = PluginStatus.DEACTIVATED
                state.active = False
                state.last_activity = datetime.utcnow()
                
                await self._emit_event(LifecycleEvent.DEACTIVATED, plugin_id, {
                    'deactivation_time_ms': (datetime.utcnow() - start_time).total_seconds() * 1000
                })
                
                # Update statistics
                self._update_stats()
                
                return True
            else:
                # Handle deactivation failure
                state.status = PluginStatus.ERROR
                state.error_count += 1
                state.last_error = "Deactivation failed"
                state.last_activity = datetime.utcnow()
                
                await self._emit_event(LifecycleEvent.ERROR_OCCURRED, plugin_id, {
                    'error': 'Deactivation failed',
                    'error_count': state.error_count
                })
                
                return False
                
        except Exception as e:
            # Handle unexpected errors
            state = self._get_or_create_state(plugin_id)
            state.status = PluginStatus.ERROR
            state.error_count += 1
            state.last_error = str(e)
            state.last_activity = datetime.utcnow()
            
            await self._emit_event(LifecycleEvent.ERROR_OCCURRED, plugin_id, {
                'error': str(e),
                'error_count': state.error_count
            })
            
            await self.error_handler.handle_error(
                PluginError(
                    plugin_id=plugin_id,
                    error_type="deactivation_error",
                    message=str(e),
                    severity=ErrorSeverity.HIGH
                )
            )
            
            return False
    
    async def cleanup_plugin(self, plugin_id: str) -> bool:
        """
        Clean up a plugin.
        
        Args:
            plugin_id: Plugin ID
            
        Returns:
            True if cleanup successful
        """
        start_time = datetime.utcnow()
        
        try:
            # Deactivate plugin first if active
            state = self._get_or_create_state(plugin_id)
            if state.active:
                await self.deactivate_plugin(plugin_id)
            
            # Update state
            state.status = PluginStatus.CLEANING_UP
            await self._emit_event(LifecycleEvent.CLEANING_UP, plugin_id)
            
            # Get plugin instance
            plugin = self._plugin_instances.get(plugin_id)
            if not plugin:
                await self._emit_event(LifecycleEvent.ERROR_OCCURRED, plugin_id, {
                    'error': 'Plugin instance not found'
                })
                return False
            
            # Get plugin context
            context = self._plugin_contexts.get(plugin_id)
            if not context:
                await self._emit_event(LifecycleEvent.ERROR_OCCURRED, plugin_id, {
                    'error': 'Plugin context not found'
                })
                return False
            
            # Clean up plugin
            cleanup_success = await plugin.cleanup(context)
            
            if cleanup_success:
                # Remove from registries
                del self._plugin_instances[plugin_id]
                del self._plugin_contexts[plugin_id]
                if plugin_id in self._weak_refs:
                    del self._weak_refs[plugin_id]
                
                # Update state
                state.status = PluginStatus.CLEANED_UP
                state.initialized = False
                state.active = False
                state.last_activity = datetime.utcnow()
                
                await self._emit_event(LifecycleEvent.CLEANED_UP, plugin_id, {
                    'cleanup_time_ms': (datetime.utcnow() - start_time).total_seconds() * 1000
                })
                
                return True
            else:
                # Handle cleanup failure
                state.status = PluginStatus.ERROR
                state.error_count += 1
                state.last_error = "Cleanup failed"
                state.last_activity = datetime.utcnow()
                
                await self._emit_event(LifecycleEvent.ERROR_OCCURRED, plugin_id, {
                    'error': 'Cleanup failed',
                    'error_count': state.error_count
                })
                
                return False
                
        except Exception as e:
            # Handle unexpected errors
            state = self._get_or_create_state(plugin_id)
            state.status = PluginStatus.ERROR
            state.error_count += 1
            state.last_error = str(e)
            state.last_activity = datetime.utcnow()
            
            await self._emit_event(LifecycleEvent.ERROR_OCCURRED, plugin_id, {
                'error': str(e),
                'error_count': state.error_count
            })
            
            await self.error_handler.handle_error(
                PluginError(
                    plugin_id=plugin_id,
                    error_type="cleanup_error",
                    message=str(e),
                    severity=ErrorSeverity.HIGH
                )
            )
            
            return False
    
    async def execute_plugin_hook(self, plugin_id: str, hook_type: HookType, **kwargs) -> PluginResult:
        """
        Execute a plugin hook.
        
        Args:
            plugin_id: Plugin ID
            hook_type: Hook type
            **kwargs: Hook arguments
            
        Returns:
            Plugin execution result
        """
        start_time = datetime.utcnow()
        
        try:
            # Check if plugin is active
            state = self._get_or_create_state(plugin_id)
            if not state.active:
                return PluginResult(
                    success=False,
                    plugin_id=plugin_id,
                    hook_type=hook_type,
                    errors=[f"Plugin {plugin_id} is not active"]
                )
            
            # Get plugin instance
            plugin = self._plugin_instances.get(plugin_id)
            if not plugin:
                return PluginResult(
                    success=False,
                    plugin_id=plugin_id,
                    hook_type=hook_type,
                    errors=[f"Plugin instance not found for {plugin_id}"]
                )
            
            # Get plugin context
            context = self._plugin_contexts.get(plugin_id)
            if not context:
                return PluginResult(
                    success=False,
                    plugin_id=plugin_id,
                    hook_type=hook_type,
                    errors=[f"Plugin context not found for {plugin_id}"]
                )
            
            # Update context with current hook info
            context.metadata.update({
                'hook_type': hook_type.value,
                'hook_args': kwargs
            })
            
            # Execute with timeout
            try:
                result = await asyncio.wait_for(
                    plugin.execute(context, hook_type, **kwargs),
                    timeout=self._max_execution_time_seconds
                )
                
                # Update statistics
                execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                state.total_execution_time_ms += execution_time_ms
                state.execution_count += 1
                state.last_activity = datetime.utcnow()
                
                # Update global stats
                self._stats['total_executions'] += 1
                self._stats['total_execution_time_ms'] += execution_time_ms
                self._stats['average_execution_time_ms'] = (
                    self._stats['total_execution_time_ms'] / self._stats['total_executions']
                )
                
                return result
                
            except asyncio.TimeoutError:
                await self._emit_event(LifecycleEvent.ERROR_OCCURRED, plugin_id, {
                    'error': f'Plugin execution timeout ({self._max_execution_time_seconds}s)',
                    'hook_type': hook_type.value
                })
                
                return PluginResult(
                    success=False,
                    plugin_id=plugin_id,
                    hook_type=hook_type,
                    errors=[f"Execution timeout after {self._max_execution_time_seconds}s"]
                )
                
        except Exception as e:
            # Handle execution errors
            state.error_count += 1
            state.last_error = str(e)
            state.last_activity = datetime.utcnow()
            
            await self._emit_event(LifecycleEvent.ERROR_OCCURRED, plugin_id, {
                'error': str(e),
                'hook_type': hook_type.value,
                'error_count': state.error_count
            })
            
            await self.error_handler.handle_error(
                PluginError(
                    plugin_id=plugin_id,
                    error_type="execution_error",
                    message=str(e),
                    severity=ErrorSeverity.MEDIUM
                )
            )
            
            execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return PluginResult(
                success=False,
                plugin_id=plugin_id,
                hook_type=hook_type,
                errors=[str(e)],
                execution_time_ms=execution_time_ms
            )
    
    async def execute_hook_for_all_plugins(self, hook_type: HookType, **kwargs) -> List[PluginResult]:
        """
        Execute a hook for all active plugins.
        
        Args:
            hook_type: Hook type
            **kwargs: Hook arguments
            
        Returns:
            List of plugin execution results
        """
        results = []
        
        # Get all active plugins
        active_plugins = [
            plugin_id for plugin_id, state in self._plugin_states.items()
            if state.active
        ]
        
        # Execute hook for each active plugin
        for plugin_id in active_plugins:
            result = await self.execute_plugin_hook(plugin_id, hook_type, **kwargs)
            results.append(result)
        
        return results
    
    async def _on_activate_plugin(self, plugin: IPlugin, context: PluginContext) -> bool:
        """Called when a plugin is activated."""
        # Override in subclasses for custom activation logic
        return True
    
    async def _on_deactivate_plugin(self, plugin: IPlugin, context: PluginContext) -> bool:
        """Called when a plugin is deactivated."""
        # Override in subclasses for custom deactivation logic
        return True
    
    def _get_or_create_state(self, plugin_id: str) -> PluginLifecycleState:
        """Get or create plugin state."""
        if plugin_id not in self._plugin_states:
            self._plugin_states[plugin_id] = PluginLifecycleState(plugin_id=plugin_id)
        
        return self._plugin_states[plugin_id]
    
    async def _cancel_plugin_executions(self, plugin_id: str) -> None:
        """Cancel all running executions for a plugin."""
        if plugin_id in self._running_executions:
            future = self._running_executions[plugin_id]
            if not future.done():
                future.cancel()
            
            del self._running_executions[plugin_id]
    
    def _update_stats(self) -> None:
        """Update plugin statistics."""
        self._stats['total_plugins'] = len(self._plugin_states)
        self._stats['active_plugins'] = len([
            state for state in self._plugin_states.values()
            if state.active
        ])
        self._stats['error_plugins'] = len([
            state for state in self._plugin_states.values()
            if state.status == PluginStatus.ERROR
        ])
    
    async def _emit_event(self, event: LifecycleEvent, plugin_id: str, 
                          details: Optional[Dict[str, Any]] = None) -> None:
        """Emit a lifecycle event."""
        record = LifecycleEventRecord(
            plugin_id=plugin_id,
            event=event,
            timestamp=datetime.utcnow(),
            details=details or {}
        )
        
        # Add to history
        self._event_history.append(record)
        
        # Notify listeners
        if event in self._event_listeners:
            for listener in self._event_listeners[event]:
                try:
                    if asyncio.iscoroutinefunction(listener):
                        await listener(record)
                    else:
                        listener(record)
                except Exception as e:
                    # Log error but don't fail
                    pass
    
    def add_event_listener(self, event: LifecycleEvent, 
                           listener: Callable[[LifecycleEventRecord], None]) -> None:
        """Add an event listener."""
        if event not in self._event_listeners:
            self._event_listeners[event] = []
        
        self._event_listeners[event].append(listener)
    
    def remove_event_listener(self, event: LifecycleEvent, 
                              listener: Callable[[LifecycleEventRecord], None]) -> bool:
        """Remove an event listener."""
        if event in self._event_listeners:
            try:
                self._event_listeners[event].remove(listener)
                return True
            except ValueError:
                pass
        
        return False
    
    def get_plugin_state(self, plugin_id: str) -> Optional[PluginLifecycleState]:
        """Get plugin state."""
        return self._plugin_states.get(plugin_id)
    
    def get_all_states(self) -> Dict[str, PluginLifecycleState]:
        """Get all plugin states."""
        return self._plugin_states.copy()
    
    def get_event_history(self, plugin_id: Optional[str] = None, 
                         event: Optional[LifecycleEvent] = None,
                         limit: Optional[int] = None) -> List[LifecycleEventRecord]:
        """Get event history."""
        history = self._event_history
        
        # Filter by plugin
        if plugin_id:
            history = [record for record in history if record.plugin_id == plugin_id]
        
        # Filter by event
        if event:
            history = [record for record in history if record.event == event]
        
        # Limit results
        if limit:
            history = history[-limit:]
        
        return history
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get lifecycle statistics."""
        stats = self._stats.copy()
        
        # Add detailed statistics
        stats['plugin_states'] = {
            status.value: len([
                state for state in self._plugin_states.values()
                if state.status == status
            ])
            for status in PluginStatus
        }
        
        stats['event_history_count'] = len(self._event_history)
        stats['running_executions'] = len(self._running_executions)
        
        return stats
    
    async def start_background_tasks(self) -> None:
        """Start background tasks."""
        # Start health check task
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        # Start cleanup task
        if self._auto_cleanup:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop_background_tasks(self) -> None:
        """Stop background tasks."""
        # Cancel health check task
        if self._health_check_task:
            self._health_check_task.cancel()
            self._health_check_task = None
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None
    
    async def _health_check_loop(self) -> None:
        """Background health check loop."""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval.total_seconds())
                await self._perform_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue
                pass
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop."""
        while True:
            try:
                await asyncio.sleep(timedelta(minutes=10).total_seconds())
                await self._perform_cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue
                pass
    
    async def _perform_health_check(self) -> None:
        """Perform health check on all plugins."""
        for plugin_id, state in self._plugin_states.items():
            if state.active:
                # Check if plugin is still responsive
                try:
                    # Get plugin instance
                    plugin = self._plugin_instances.get(plugin_id)
                    if plugin:
                        # Perform health check
                        context = self._plugin_contexts.get(plugin_id)
                        if context:
                            # Simple health check - try to get telemetry
                            telemetry = plugin.get_telemetry()
                            
                            # Check for error conditions
                            if telemetry.get('error_count', 0) > state.error_count:
                                await self._emit_event(LifecycleEvent.ERROR_OCCURRED, plugin_id, {
                                    'error': 'Plugin error count increased',
                                    'error_count': telemetry['error_count']
                                })
                except Exception as e:
                    await self._emit_event(LifecycleEvent.ERROR_OCCURRED, plugin_id, {
                        'error': f'Health check failed: {str(e)}'
                    })
    
    async def _perform_cleanup(self) -> None:
        """Perform cleanup of inactive or error plugins."""
        for plugin_id, state in list(self._plugin_states.items()):
            # Clean up plugins with too many errors
            if state.error_count >= self._max_error_count:
                await self.cleanup_plugin(plugin_id)
            
            # Clean up inactive plugins that haven't been used recently
            elif (not state.active and 
                  state.last_activity and 
                  datetime.utcnow() - state.last_activity > timedelta(hours=1)):
                await self.cleanup_plugin(plugin_id)
    
    def shutdown(self) -> None:
        """Shutdown the lifecycle manager."""
        # Stop background tasks
        asyncio.create_task(self.stop_background_tasks())
        
        # Cancel all running executions
        for future in self._running_executions.values():
            if not future.done():
                future.cancel()
        
        # Clean up all plugins
        for plugin_id in list(self._plugin_instances.keys()):
            asyncio.create_task(self.cleanup_plugin(plugin_id))
        
        # Clear registries
        self._plugin_states.clear()
        self._plugin_instances.clear()
        self._plugin_contexts.clear()
        self._weak_refs.clear()
        
        # Shutdown executor
        self._executor.shutdown(wait=True)


# Global plugin lifecycle manager instance
_plugin_lifecycle_manager = PluginLifecycleManager()


# Convenience functions
async def initialize_plugin(plugin_id: str, context: PluginContext) -> bool:
    """Initialize a plugin."""
    return await _plugin_lifecycle_manager.initialize_plugin(plugin_id, context)


async def activate_plugin(plugin_id: str) -> bool:
    """Activate a plugin."""
    return await _plugin_lifecycle_manager.activate_plugin(plugin_id)


async def deactivate_plugin(plugin_id: str) -> bool:
    """Deactivate a plugin."""
    return await _plugin_lifecycle_manager.deactivate_plugin(plugin_id)


async def cleanup_plugin(plugin_id: str) -> bool:
    """Clean up a plugin."""
    return await _plugin_lifecycle_manager.cleanup_plugin(plugin_id)


async def execute_plugin_hook(plugin_id: str, hook_type: HookType, **kwargs) -> PluginResult:
    """Execute a plugin hook."""
    return await _plugin_lifecycle_manager.execute_plugin_hook(plugin_id, hook_type, **kwargs)


async def execute_hook_for_all_plugins(hook_type: HookType, **kwargs) -> List[PluginResult]:
    """Execute a hook for all active plugins."""
    return await _plugin_lifecycle_manager.execute_hook_for_all_plugins(hook_type, **kwargs)


def get_plugin_state(plugin_id: str) -> Optional[PluginLifecycleState]:
    """Get plugin state."""
    return _plugin_lifecycle_manager.get_plugin_state(plugin_id)


def get_all_states() -> Dict[str, PluginLifecycleState]:
    """Get all plugin states."""
    return _plugin_lifecycle_manager.get_all_states()


def get_statistics() -> Dict[str, Any]:
    """Get lifecycle statistics."""
    return _plugin_lifecycle_manager.get_statistics()


def get_plugin_lifecycle_manager() -> PluginLifecycleManager:
    """Get the global plugin lifecycle manager."""
    return _plugin_lifecycle_manager
