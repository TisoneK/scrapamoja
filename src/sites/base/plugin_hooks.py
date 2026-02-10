"""
Plugin hook system for the scraper framework.

This module provides comprehensive hook management, including hook registration,
execution, priority handling, and event propagation.
"""

import asyncio
import threading
import time
from typing import Dict, Any, List, Optional, Callable, Union, Type
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import inspect
import weakref

from .plugin_interface import (
    IPlugin, PluginContext, PluginResult, PluginStatus, HookType,
    PluginMetadata, get_plugin_registry
)
from .plugin_lifecycle import get_plugin_lifecycle_manager


class HookExecutionMode(Enum):
    """Hook execution mode enumeration."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PARALLEL_WITH_ERROR_HANDLING = "parallel_with_error_handling"


class HookPropagation(Enum):
    """Hook propagation enumeration."""
    CONTINUE_ON_ERROR = "continue_on_error"
    STOP_ON_ERROR = "stop_on_error"
    COLLECT_ALL_ERRORS = "collect_all_errors"


@dataclass
class HookRegistration:
    """Hook registration information."""
    hook_id: str
    plugin_id: str
    hook_type: HookType
    callback: Callable
    priority: int = 0
    condition: Optional[Callable] = None
    enabled: bool = True
    execution_count: int = 0
    total_execution_time_ms: float = 0.0
    last_execution: Optional[datetime] = None
    last_result: Optional[PluginResult] = None
    error_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization validation."""
        if not self.hook_id:
            self.hook_id = f"{self.plugin_id}_{self.hook_type.value}_{id(self.callback)}"


@dataclass
class HookExecutionContext:
    """Hook execution context."""
    hook_type: HookType
    hook_id: str
    plugin_id: str
    execution_id: str
    start_time: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    context: Optional[PluginContext] = None
    arguments: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization validation."""
        self.execution_id = str(int(time.time() * 1000000))


@dataclass
class HookExecutionResult:
    """Hook execution result."""
    hook_id: str
    plugin_id: str
    hook_type: HookType
    success: bool
    result: Optional[PluginResult] = None
    execution_time_ms: float = 0.0
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class HookManager:
    """Hook management system."""
    
    def __init__(self):
        """Initialize hook manager."""
        self._hooks: Dict[HookType, List[HookRegistration]] = defaultdict(list)
        self._hook_index: Dict[str, HookRegistration] = {}
        self._execution_mode = HookExecutionMode.SEQUENTIAL
        self._propagation = HookPropagation.CONTINUE_ON_ERROR
        self._max_concurrent_executions = 10
        self._execution_timeout_seconds = 30
        
        # Execution tracking
        self._running_executions: Dict[str, asyncio.Task] = {}
        self._execution_history: List[HookExecutionResult] = []
        
        # Statistics
        self._stats = {
            'total_hooks': 0,
            'total_executions': 0,
            'total_execution_time_ms': 0.0,
            'average_execution_time_ms': 0.0,
            'error_count': 0,
            'execution_count_by_type': {},
            'execution_count_by_plugin': {}
        }
        
        # Event listeners
        self._event_listeners: Dict[str, List[Callable]] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Weak references for cleanup
        self._weak_refs: Dict[str, weakref.ref] = {}
    
    def register_hook(self, plugin_id: str, hook_type: HookType, 
                     callback: Callable, priority: int = 0,
                     condition: Optional[Callable] = None,
                     hook_id: Optional[str] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Register a hook.
        
        Args:
            plugin_id: Plugin ID
            hook_type: Hook type
            callback: Hook callback
            priority: Hook priority (higher = executed first)
            condition: Condition function
            hook_id: Hook ID (auto-generated if None)
            metadata: Additional metadata
            
        Returns:
            Hook ID
        """
        with self._lock:
            # Generate hook ID if not provided
            if not hook_id:
                hook_id = f"{plugin_id}_{hook_type.value}_{id(callback)}"
            
            # Check for duplicate registration
            if hook_id in self._hook_index:
                raise ValueError(f"Hook ID {hook_id} already registered")
            
            # Create registration
            registration = HookRegistration(
                hook_id=hook_id,
                plugin_id=plugin_id,
                hook_type=hook_type,
                callback=callback,
                priority=priority,
                condition=condition,
                metadata=metadata or {}
            )
            
            # Add to hooks list
            self._hooks[hook_type].append(registration)
            
            # Sort by priority (higher first)
            self._hooks[hook_type].sort(key=lambda r: r.priority, reverse=True)
            
            # Add to index
            self._hook_index[hook_id] = registration
            
            # Create weak reference for cleanup
            if hasattr(callback, '__self__'):
                self._weak_refs[hook_id] = weakref.ref(callback)
            
            # Update statistics
            self._stats['total_hooks'] += 1
            
            # Emit event
            self._emit_event('hook_registered', {
                'hook_id': hook_id,
                'plugin_id': plugin_id,
                'hook_type': hook_type.value,
                'priority': priority
            })
            
            return hook_id
    
    def unregister_hook(self, hook_id: str) -> bool:
        """
        Unregister a hook.
        
        Args:
            hook_id: Hook ID
            
        Returns:
            True if unregistered successfully
        """
        with self._lock:
            if hook_id not in self._hook_index:
                return False
            
            registration = self._hook_index[hook_id]
            
            # Remove from hooks list
            if registration.hook_type in self._hooks:
                try:
                    self._hooks[registration.hook_type].remove(registration)
                except ValueError:
                    pass  # Already removed
            
            # Remove from index
            del self._hook_index[hook_id]
            
            # Remove weak reference
            if hook_id in self._weak_refs:
                del self._weak_refs[hook_id]
            
            # Update statistics
            self._stats['total_hooks'] = max(0, self._stats['total_hooks'] - 1)
            
            # Emit event
            self._emit_event('hook_unregistered', {
                'hook_id': hook_id,
                'plugin_id': registration.plugin_id,
                'hook_type': registration.hook_type.value
            })
            
            return True
    
    def get_hooks(self, hook_type: HookType) -> List[HookRegistration]:
        """Get all hooks for a specific type."""
        with self._lock:
            return self._hooks.get(hook_type, []).copy()
    
    def get_hook(self, hook_id: str) -> Optional[HookRegistration]:
        """Get a specific hook by ID."""
        with self._lock:
            return self._hook_index.get(hook_id)
    
    def get_all_hooks(self) -> Dict[HookType, List[HookRegistration]]:
        """Get all hooks by type."""
        with self._lock:
            return {k: v.copy() for k, v in self._hooks.items()}
    
    def enable_hook(self, hook_id: str) -> bool:
        """Enable a hook."""
        with self._lock:
            registration = self._hook_index.get(hook_id)
            if registration:
                registration.enabled = True
                registration.updated_at = datetime.utcnow()
                
                self._emit_event('hook_enabled', {
                    'hook_id': hook_id,
                    'plugin_id': registration.plugin_id,
                    'hook_type': registration.hook_type.value
                })
                
                return True
            return False
    
    def disable_hook(self, hook_id: str) -> bool:
        """Disable a hook."""
        with self._lock:
            registration = self._hook_index.get(hook_id)
            if registration:
                registration.enabled = False
                registration.updated_at = datetime.utcnow()
                
                self._emit_event('hook_disabled', {
                    'hook_id': hook_id,
                    'plugin_id': registration.plugin_id,
                    'hook_type': registration.hook_type.value
                })
                
                return True
            return False
    
    def set_execution_mode(self, mode: HookExecutionMode) -> None:
        """Set hook execution mode."""
        self._execution_mode = mode
    
    def set_propagation(self, propagation: HookPropagation) -> None:
        """Set hook propagation mode."""
        self._propagation = propagation
    
    def set_max_concurrent_executions(self, max_executions: int) -> None:
        """Set maximum concurrent executions."""
        self._max_concurrent_executions = max_executions
    
    def set_execution_timeout(self, timeout_seconds: int) -> None:
        """Set execution timeout in seconds."""
        self._execution_timeout_seconds = timeout_seconds
    
    async def execute_hook(self, hook_id: str, **kwargs) -> HookExecutionResult:
        """
        Execute a specific hook.
        
        Args:
            hook_id: Hook ID
            **kwargs: Hook arguments
            
        Returns:
            Hook execution result
        """
        start_time = datetime.utcnow()
        
        try:
            # Get hook registration
            registration = self.get_hook(hook_id)
            if not registration:
                return HookExecutionResult(
                    hook_id=hook_id,
                    plugin_id="",
                    hook_type=HookType.CUSTOM,
                    success=False,
                    error=f"Hook {hook_id} not found",
                    execution_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
                )
            
            # Check if hook is enabled
            if not registration.enabled:
                return HookExecutionResult(
                    hook_id=hook_id,
                    plugin_id=registration.plugin_id,
                    hook_type=registration.hook_type,
                    success=False,
                    error=f"Hook {hook_id} is disabled",
                    execution_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
                )
            
            # Check condition
            if registration.condition:
                try:
                    # Create mock context for condition check
                    mock_context = MockPluginContext()
                    
                    if not registration.condition(mock_context, **kwargs):
                        return HookExecutionResult(
                            hook_id=hook_id,
                            plugin_id=registration.plugin_id,
                            hook_type=registration.hook_type,
                            success=True,
                            data={"skipped": True, "reason": "condition_not_met"},
                            execution_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
                        )
                except Exception as e:
                    return HookExecutionResult(
                        hook_id=hook_id,
                        plugin_id=registration.plugin_id,
                        hook_type=registration.hook_type,
                        success=False,
                        error=f"Condition check failed: {str(e)}",
                        execution_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
                    )
            
            # Get plugin instance
            plugin = get_plugin_registry().get_plugin(registration.plugin_id)
            if not plugin:
                return HookExecutionResult(
                    hook_id=hook_id,
                    plugin_id=registration.plugin_id,
                    hook_type=registration.hook_type,
                    success=False,
                    error=f"Plugin {registration.plugin_id} not found",
                    execution_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
                )
            
            # Get plugin context
            lifecycle_manager = get_plugin_lifecycle_manager()
            context = lifecycle_manager.get_plugin_context(registration.plugin_id)
            
            if not context:
                return HookExecutionResult(
                    hook_id=hook_id,
                    plugin_id=registration.plugin_id,
                    hook_type=registration.hook_type,
                    success=False,
                    error=f"Plugin {registration.plugin_id} not initialized",
                    execution_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
                )
            
            # Create execution context
            exec_context = HookExecutionContext(
                hook_type=registration.hook_type,
                hook_id=hook_id,
                plugin_id=registration.plugin_id,
                execution_id=str(int(time.time() * 1000000)),
                start_time=start_time,
                context=context,
                arguments=kwargs
            )
            
            # Execute hook
            try:
                if inspect.iscoroutinefunction(registration.callback):
                    result = await asyncio.wait_for(
                        registration.callback(exec_context, **kwargs),
                        timeout=self._execution_timeout_seconds
                    )
                else:
                    result = registration.callback(exec_context, **kwargs)
                
                # Convert result to PluginResult if needed
                if isinstance(result, PluginResult):
                    plugin_result = result
                elif isinstance(result, dict):
                    plugin_result = PluginResult(
                        success=True,
                        plugin_id=registration.plugin_id,
                        hook_type=registration.hook_type,
                        data=result,
                        execution_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
                    )
                elif isinstance(result, bool):
                    plugin_result = PluginResult(
                        success=result,
                        plugin_id=registration.plugin_id,
                        registration.hook_type,
                        execution_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
                    )
                else:
                    plugin_result = PluginResult(
                        success=True,
                        plugin_id=registration.plugin_id,
                        registration.hook_type,
                        data={"result": result},
                        execution_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
                    )
                
                # Update registration statistics
                registration.execution_count += 1
                registration.total_execution_time_ms += plugin_result.execution_time_ms
                registration.last_execution = datetime.utcnow()
                registration.last_result = plugin_result
                registration.updated_at = datetime.utcnow()
                
                if not plugin_result.success:
                    registration.error_count += 1
                
                # Update global statistics
                self._update_stats(registration, plugin_result)
                
                # Store in history
                execution_result = HookExecutionResult(
                    hook_id=hook_id,
                    plugin_id=registration.plugin_id,
                    hook_type=registration.hook_type,
                    success=plugin_result.success,
                    result=plugin_result,
                    execution_time_ms=plugin_result.execution_time_ms,
                    error=plugin_result.errors[0] if plugin_result.errors else None,
                    warnings=plugin_result.warnings,
                    metadata=exec_context.metadata
                )
                
                self._execution_history.append(execution_result)
                
                # Emit event
                self._emit_event('hook_executed', {
                    'hook_id': hook_id,
                    'plugin_id': registration.plugin_id,
                    'hook_type': registration.hook_type.value,
                    'success': plugin_result.success,
                    'execution_time_ms': plugin_result.execution_time_ms,
                    'error_count': registration.error_count
                })
                
                return execution_result
                
            except asyncio.TimeoutError:
                execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                # Update registration statistics
                registration.error_count += 1
                registration.last_execution = datetime.utcnow()
                registration.updated_at = datetime.utcnow()
                
                self._update_stats(registration, None)
                
                return HookExecutionResult(
                    hook_id=hook_id,
                    plugin_id=registration.plugin_id,
                    hook_type=registration.hook_type,
                    success=False,
                    error=f"Execution timeout after {self._execution_timeout_seconds}s",
                    execution_time_ms=execution_time_ms
                )
                
            except Exception as e:
                execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                # Update registration statistics
                registration.error_count += 1
                registration.last_execution = datetime.utcnow()
                registration.updated_at = datetime.utcnow()
                
                self._update_stats(registration, None)
                
                return HookExecutionResult(
                    hook_id=hook_id,
                    plugin_id=registration.plugin_id,
                    hook_type=registration.hook_type,
                    success=False,
                    error=str(e),
                    execution_time_ms=execution_time_ms
                )
                
        except Exception as e:
            return HookExecutionResult(
                hook_id=hook_id,
                plugin_id="",
                hook_type=HookType.CUSTOM,
                success=False,
                error=f"Hook execution failed: {str(e)}",
                execution_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
            )
    
    async def execute_hooks(self, hook_type: HookType, **kwargs) -> List[HookExecutionResult]:
        """
        Execute all hooks for a specific type.
        
        args:
            hook_type: Hook type
            **kwargs: Hook arguments
            
        Returns:
            List of hook execution results
        """
        start_time = datetime.utcnow()
        
        try:
            # Get all hooks for this type
            hooks = self.get_hooks(hook_type)
            
            if not hooks:
                return []
            
            if self._execution_mode == HookExecutionMode.SEQUENTIAL:
                return await self._execute_sequential(hooks, **kwargs)
            elif self._execution_mode == HookExecutionMode.PARALLEL:
                return await self._execute_parallel(hooks, **kwargs)
            elif self._execution_mode == HookExecutionMode.PARALLEL_WITH_ERROR_HANDLING:
                return await self._execute_parallel_with_error_handling(hooks, **kwargs)
            else:
                raise ValueError(f"Unknown execution mode: {self._execution_mode}")
                
        except Exception as e:
            return [
                HookExecutionResult(
                    hook_id="",
                    plugin_id="",
                    hook_type=hook_type,
                    success=False,
                    error=f"Hook execution failed: {str(e)}",
                    execution_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
                )
            ]
    
    async def _execute_sequential(self, hooks: List[HookRegistration], **kwargs) -> List[HookExecutionResult]:
        """Execute hooks sequentially."""
        results = []
        
        for hook in hooks:
            result = await self.execute_hook(hook.hook_id, **kwargs)
            results.append(result)
            
            # Check propagation mode
            if not result.success and self._propagation == HookPropagation.STOP_ON_ERROR:
                break
            elif not result.success and self._propagation == HookPropagation.COLLECT_ALL_ERRORS:
                continue  # Continue collecting all errors
        
        return results
    
    async def _execute_parallel(self, hooks: List[HookRegistration], **kwargs) -> List[HookExecutionResult]:
        """Execute hooks in parallel."""
        # Limit concurrent executions
        hooks = hooks[:self._max_concurrent_executions]
        
        # Create tasks
        tasks = []
        for hook in hooks:
            task = asyncio.create_task(self.execute_hook(hook.hook_id, **kwargs))
            tasks.append(task)
            self._running_executions[hook.hook_id] = task
        
        try:
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks)
            
            # Clean up running executions
            for hook_id in list(self._running_executions.keys()):
                if hook_id in [task.get_name() for task in tasks if task.done()]:
                    del self._running_executions[hook_id]
            
            return results
            
        except Exception as e:
            # Cancel all tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
            
            return [
                HookExecutionResult(
                    hook_id="",
                    plugin_id="",
                    hook_type=HookType.CUSTOM,
                    success=False,
                    error=f"Parallel execution failed: {str(e)}",
                    execution_time_ms=0
                )
            ] for _ in hooks
        finally:
            # Clean up running executions
            for hook_id in list(self._running_executions.keys()):
                del self._running_executions[hook_id]
    
    async def _execute_parallel_with_error_handling(self, hooks: List[HookRegistration], **kwargs) -> List[HookExecutionResult]:
        """Execute hooks in parallel with error handling."""
        # Limit concurrent executions
        hooks = hooks[:self._max_concurrent_executions]
        
        # Create tasks
        tasks = []
        for hook in hooks:
            task = asyncio.create_task(self._execute_hook(hook.hook_id, **kwargs))
            tasks.append(task)
            self._running_executions[hook.hook_id] = task
        
        try:
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks)
            
            # Clean up running executions
            for hook_id in list(self._running_executions.keys()):
                if hook_id in [task.get_name() for task in tasks if task.done()]:
                    del self._running_executions[hook_id]
            
            return results
            
        except Exception as e:
            # Cancel all tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
            
            return [
                HookExecutionResult(
                    hook_id="",
                    plugin_id="",
                    hook_type=HookType.CUSTOM,
                    success=False,
                    error=f"Parallel execution with error handling failed: {str(e)}",
                    execution_time_ms=0
                )
            ] for _ in hooks
        finally:
            # Clean up running executions
            for hook_id in list(self._running_executions.keys()):
                del self._running_executions[hook_id]
    
    def _update_stats(self, registration: Optional[HookRegistration] = None, result: Optional[PluginResult] = None) -> None:
        """Update hook statistics."""
        if registration:
            # Update type statistics
            hook_type = registration.hook_type.value
            self._stats['execution_count_by_type'][hook_type] = registration.execution_count
            
            # Update plugin statistics
            self._stats['execution_count_by_plugin'][registration.plugin_id] = registration.execution_count
        
        if result:
            self._stats['total_executions'] += 1
            self._stats['total_execution_time_ms'] += result.execution_time_ms
            self._stats['average_execution_time_ms'] = (
                self._stats['total_execution_time_ms'] / self._class__stats['total_executions']
                if self._stats['total_executions'] > 0 else 0
            )
            
            if not result.success:
                self._stats['error_count'] += 1
    
    def get_hook_statistics(self, hook_id: Optional[str] = None, 
                           hook_type: Optional[HookType] = None) -> Dict[str, Any]:
        """Get hook statistics."""
        stats = self._stats.copy()
        
        if hook_id:
            registration = self.get_hook(hook_id)
            if registration:
                stats['hook'] = {
                    'execution_count': registration.execution_count,
                    'total_execution_time_ms': registration.total_execution_time_ms,
                    'average_execution_time_ms': (
                        registration.total_execution_time_ms / registration.execution_count
                        if registration.execution_count > 0 else 0
                    ),
                    'error_count': registration.error_count,
                    'last_execution': registration.last_execution.isoformat() if registration.last_execution else None,
                    'enabled': registration.enabled,
                    'priority': registration.priority
                }
        
        elif hook_type:
            hooks = self.get_hooks(hook_type)
            stats['hooks'] = {
                'count': len(hooks),
                'enabled_count': len([h for h in hooks if h.enabled]),
                'total_executions': sum(h.execution_count for h in hooks),
                'total_execution_time_ms': sum(h.total_execution_time_ms for h in hooks),
                'average_execution_time_ms': (
                    sum(h.total_execution_time_ms for h in hooks) / len(hooks)
                    if hooks else 0
                ),
                'error_count': sum(h.error_count for h in hooks)
            }
        
        return stats
    
    def get_execution_history(self, hook_id: Optional[str] = None,
                           hook_type: Optional[HookType] = None,
                           plugin_id: Optional[str] = None,
                           limit: Optional[int] = None) -> List[HookExecutionResult]:
        """Get execution history."""
        history = self._execution_history
        
        # Filter by hook_id
        if hook_id:
            history = [result for result in history if result.hook_id == hook_id]
        
        # Filter by hook type
        if hook_type:
            history = [result for result in history if result.hook_type == hook_type]
        
        # Filter by plugin id
        if plugin_id:
            history = [result for result in history if result.plugin_id == plugin_id]
        
        # Limit results
        if limit:
            history = history[-limit:]
        
        return history
    
    def add_event_listener(self, event: str, listener: Callable) -> None:
        """Add an event listener."""
        if event not in self._event_listeners:
            self._event_listeners[event] = []
        
        self._event_listeners[event].append(listener)
    
    def remove_event_listener(self, event: str, listener: Callable) -> bool:
        """Remove an event listener."""
        if event in self._event_listeners:
            try:
                self._event_listeners[event].remove(listener)
                return True
            except ValueError:
                    pass
        
        return False
    
    def _emit_event(self, event: str, data: Dict[str, Any]) -> None:
        """Emit an event to listeners."""
        if event in self._event_listeners:
            for listener in self._event_listeners[event]:
                try:
                    listener(data)
                except Exception as e:
                    # Log error but continue
                    pass
    
    def clear_history(self) -> None:
        """Clear execution history."""
        self._execution_history.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get hook statistics."""
        return self._stats.copy()
    
    def cleanup(self) -> None:
        """Clean up hook manager."""
        # Cancel running executions
        for task in self._running_executions.values():
            if not task.done():
                task.cancel()
        
        # Clear registries
        self._hooks.clear()
        self._hook_index.clear()
        self._weak_refs.clear()
        
        # Clear history
        self._execution_history.clear()
        
        # Clear event listeners
        self._event_listeners.clear()
        
        # Reset statistics
        self._stats = {
            'total_hooks': 0,
            'total_executions': 0,
            'total_execution_time_ms': 0.0,
            'average_execution_time_ms': 0.0,
            'error_count': 0,
            'execution_count_by_type': {},
            'execution_count_by_plugin': {}
        }


class MockPluginContext:
    """Mock plugin context for testing."""
    
    def __init__(self):
        """Initialize mock context."""
        self.plugin_id = "mock_plugin"
        self.framework_context = None
        self.configuration = {}
        self.metadata = {}


# Global hook manager instance
_hook_manager = HookManager()


# Convenience functions
def register_hook(plugin_id: str, hook_type: HookType, callback: Callable,
                 priority: int = 0, condition: Optional[Callable] = None,
                 hook_id: Optional[str] = None) -> str:
    """Register a hook."""
    return _hook_manager.register_hook(
        plugin_id, hook_type, callback, priority, condition, hook_id
    )


def unregister_hook(hook_id: str) -> bool:
    """Unregister a hook."""
    return _hook_manager.unregister_hook(hook_id)


def get_hooks(hook_type: HookType) -> List[HookRegistration]:
    """Get all hooks for a specific type."""
    return _hook_manager.get_hooks(hook_type)


def get_hook(hook_id: str) -> Optional[HookRegistration]:
    """Get a specific hook by ID."""
    return _hook_manager.get_hook(hook_id)


def get_all_hooks() -> Dict[str, List[HookRegistration]]:
    """Get all hooks by type."""
    return _hook_manager.get_all_hooks()


async def execute_hook(hook_id: str, **kwargs) -> HookExecutionResult:
    """Execute a specific hook."""
    return await _hook_manager.execute_hook(hook_id, **kwargs)


async def execute_hooks(hook_type: HookType, **kwargs) -> List[HookExecutionResult]:
    """Execute all hooks for a specific type."""
    return await _hook_manager.execute_hooks(hook_type, **kwargs)


def get_hook_statistics(hook_id: Optional[str] = None,
                     hook_type: Optional[HookType] = None) -> Dict[str, Any]:
    """Get hook statistics."""
    return _hook_manager.get_statistics(hook_id, hook_type)


def get_execution_history(hook_id: Optional[str] = None,
                           hook_type: Optional[HookType] = None,
                           plugin_id: Optional[str] = None,
                           limit: Optional[int] = None) -> List[HookExecutionResult]:
    """Get execution history."""
    return _hook_manager.get_execution_history(hook_id, hook_type, plugin_id, limit)


def get_hook_manager() -> HookManager:
    """Get the global hook manager."""
    return _hook_manager
