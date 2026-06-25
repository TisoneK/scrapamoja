"""
Custom interrupt callback registration API.
"""

import asyncio
import logging
import time
import inspect
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum

from .handler import InterruptHandler, InterruptContext
from .config import InterruptConfig


class CallbackPriority(Enum):
    """Priority levels for interrupt callbacks."""
    CRITICAL = 100    # Critical cleanup operations
    HIGH = 80         # High priority operations
    NORMAL = 50        # Normal priority operations
    LOW = 20           # Low priority operations
    BACKGROUND = 10     # Background/maintenance operations


class CallbackType(Enum):
    """Types of interrupt callbacks."""
    CLEANUP = "cleanup"
    DATA_PRESERVATION = "data_preservation"
    USER_NOTIFICATION = "user_notification"
    CUSTOM = "custom"
    SYSTEM = "system"


@dataclass
class CallbackMetadata:
    """Metadata for an interrupt callback."""
    name: str
    callback_type: CallbackType
    priority: CallbackPriority
    timeout: Optional[float] = None
    description: str = ""
    category: str = "general"
    retry_count: int = 0
    max_retries: int = 0
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class CallbackExecution:
    """Execution information for a callback."""
    callback_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    success: bool = False
    error: Optional[Exception] = None
    retry_count: int = 0
    execution_context: Optional[Dict[str, Any]] = None


class InterruptCallbackRegistry:
    """Registry for custom interrupt callbacks with advanced management."""
    
    def __init__(self, interrupt_handler: InterruptHandler, config: InterruptConfig):
        self.interrupt_handler = interrupt_handler
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Callback storage
        self.callbacks: Dict[str, CallbackMetadata] = {}
        self.execution_history: List[CallbackExecution] = []
        
        # Execution state
        self._executing_callbacks: set = set()
        self._execution_lock = asyncio.Lock()
        
        # Statistics
        self.stats = {
            'total_registrations': 0,
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'average_execution_time': 0.0,
            'callbacks_by_type': {},
            'callbacks_by_priority': {}
        }
    
    def register_callback(self, 
                       name: str,
                       callback: Callable,
                       callback_type: CallbackType = CallbackType.CUSTOM,
                       priority: CallbackPriority = CallbackPriority.NORMAL,
                       timeout: Optional[float] = None,
                       description: str = "",
                       category: str = "general",
                       max_retries: int = 0,
                       dependencies: List[str] = None,
                       tags: List[str] = None) -> bool:
        """
        Register a custom interrupt callback.
        
        Args:
            name: Unique name for the callback
            callback: The callback function to execute
            callback_type: Type of callback (cleanup, data_preservation, etc.)
            priority: Priority level for execution order
            timeout: Maximum execution time in seconds
            description: Human-readable description
            category: Category for grouping
            max_retries: Maximum retry attempts on failure
            dependencies: List of callback names that must execute first
            tags: List of tags for filtering and management
            
        Returns:
            True if registration successful, False otherwise
        """
        if name in self.callbacks:
            self.logger.warning(f"Callback {name} already registered")
            return False
        
        # Validate callback
        if not callable(callback):
            self.logger.error(f"Callback {name} is not callable")
            return False
        
        # Create metadata
        metadata = CallbackMetadata(
            name=name,
            callback_type=callback_type,
            priority=priority,
            timeout=timeout or self.config.default_cleanup_timeout,
            description=description,
            category=category,
            max_retries=max_retries,
            dependencies=dependencies or [],
            tags=tags or []
        )
        
        # Store callback
        self.callbacks[name] = metadata
        
        # Update statistics
        self.stats['total_registrations'] += 1
        self._update_type_stats(callback_type.value, 1)
        self._update_priority_stats(priority.value, 1)
        
        # Register with interrupt handler
        self.interrupt_handler.register_interrupt_callback(
            self._create_wrapper_callback(name, metadata)
        )
        
        self.logger.info(f"Registered callback: {name} (type: {callback_type.value}, priority: {priority.value})")
        return True
    
    def unregister_callback(self, name: str) -> bool:
        """
        Unregister a callback by name.
        
        Args:
            name: Name of the callback to unregister
            
        Returns:
            True if unregistered successfully, False if not found
        """
        if name not in self.callbacks:
            self.logger.warning(f"Callback {name} not found for unregistration")
            return False
        
        metadata = self.callbacks.pop(name)
        
        # Update statistics
        self._update_type_stats(metadata.callback_type.value, -1)
        
        self.logger.info(f"Unregistered callback: {name}")
        return True
    
    def get_callback(self, name: str) -> Optional[CallbackMetadata]:
        """Get callback metadata by name."""
        return self.callbacks.get(name)
    
    def list_callbacks(self, 
                   callback_type: Optional[CallbackType] = None,
                   category: Optional[str] = None,
                   priority: Optional[CallbackPriority] = None,
                   tags: Optional[List[str]] = None) -> List[CallbackMetadata]:
        """
        List callbacks with optional filtering.
        
        Args:
            callback_type: Filter by callback type
            category: Filter by category
            priority: Filter by priority level
            tags: Filter by tags (callback must have all specified tags)
            
        Returns:
            List of matching callback metadata
        """
        callbacks = list(self.callbacks.values())
        
        # Apply filters
        if callback_type:
            callbacks = [c for c in callbacks if c.callback_type == callback_type]
        
        if category:
            callbacks = [c for c in callbacks if c.category == category]
        
        if priority:
            callbacks = [c for c in callbacks if c.priority == priority]
        
        if tags:
            callbacks = [
                c for c in callbacks 
                if all(tag in c.tags for tag in tags)
            ]
        
        return callbacks
    
    def get_callbacks_by_priority(self) -> List[CallbackMetadata]:
        """Get all callbacks sorted by priority (highest first)."""
        return sorted(
            self.callbacks.values(),
            key=lambda c: c.priority.value,
            reverse=True
        )
    
    def get_execution_plan(self) -> List[str]:
        """Get the execution order for callbacks based on dependencies and priorities."""
        # Sort by priority first
        sorted_callbacks = self.get_callbacks_by_priority()
        
        # Resolve dependencies
        execution_plan = []
        processed = set()
        
        for callback in sorted_callbacks:
            if callback.name in processed:
                continue
            
            # Check if all dependencies are satisfied
            if all(dep in processed for dep in callback.dependencies):
                execution_plan.append(callback.name)
                processed.add(callback.name)
        
        # Add any remaining callbacks
        for callback in sorted_callbacks:
            if callback.name not in processed:
                execution_plan.append(callback.name)
                processed.add(callback.name)
        
        return execution_plan
    
    async def execute_callbacks(self, context: InterruptContext) -> Dict[str, Any]:
        """
        Execute all registered callbacks during interrupt.
        
        Args:
            context: The interrupt context containing signal information
            
        Returns:
            Dictionary mapping callback names to execution results
        """
        async with self._execution_lock:
            execution_plan = self.get_execution_plan()
            results = {}
            
            self.logger.info(f"Executing {len(execution_plan)} callbacks in priority order")
            
            for callback_name in execution_plan:
                if callback_name not in self.callbacks:
                    continue
                
                metadata = self.callbacks[callback_name]
                
                try:
                    # Create execution record
                    execution = CallbackExecution(
                        callback_name=callback_name,
                        start_time=time.time()
                    )
                    
                    self._executing_callbacks.add(callback_name)
                    
                    # Execute with timeout
                    result = await self._execute_single_callback(
                        metadata.callback, metadata.timeout, context
                    )
                    
                    # Update execution record
                    execution.end_time = time.time()
                    execution.duration = execution.end_time - execution.start_time
                    execution.success = True
                    execution.execution_context = {
                        'interrupt_signal': context.signal_name,
                        'interrupt_number': context.signal_number,
                        'execution_time': execution.duration
                    }
                    
                    self.stats['total_executions'] += 1
                    self.stats['successful_executions'] += 1
                    self.stats['average_execution_time'] = (
                        (self.stats['average_execution_time'] * (self.stats['total_executions'] - 1) + 
                         execution.duration) / self.stats['total_executions']
                    )
                    
                    results[callback_name] = result
                    
                except Exception as e:
                    # Handle execution failure
                    execution.end_time = time.time()
                    execution.duration = execution.end_time - execution.start_time
                    execution.success = False
                    execution.error = e
                    execution.execution_context = {
                        'interrupt_signal': context.signal_name,
                        'interrupt_number': context.signal_number,
                        'error': str(e)
                    }
                    
                    self.stats['total_executions'] += 1
                    self.stats['failed_executions'] += 1
                    
                    results[callback_name] = {'error': str(e)}
                    
                finally:
                    self._executing_callbacks.discard(callback_name)
                    self.execution_history.append(execution)
            
            return results
    
    async def _execute_single_callback(self, 
                                   callback: Callable, 
                                   timeout: float, 
                                   context: InterruptContext) -> Any:
        """Execute a single callback with timeout and retry logic."""
        last_exception = None
        
        for attempt in range(3):  # Max 3 attempts
            try:
                if inspect.iscoroutinefunction(callback):
                    result = await asyncio.wait_for(callback(context), timeout=timeout)
                else:
                    result = callback(context)
                
                return result
                
            except asyncio.TimeoutError:
                last_exception = Exception(f"Callback execution timed out after {timeout}s")
                if attempt < 2:  # Retry on timeout
                    self.logger.warning(f"Callback timeout, retrying (attempt {attempt + 1})")
                    await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    raise last_exception
                    
            except Exception as e:
                last_exception = e
                if attempt < 2:  # Retry on exception
                    self.logger.warning(f"Callback failed, retrying (attempt {attempt + 1}): {e}")
                    await asyncio.sleep(0.1 * (attempt + 1))
                    continue
                else:
                    raise last_exception
        
        # Should not reach here, but just in case
        raise last_exception
    
    def _create_wrapper_callback(self, name: str, metadata: CallbackMetadata) -> Callable:
        """Create a wrapper callback for execution tracking."""
        async def wrapper(context: InterruptContext):
            try:
                # Log callback start
                self.logger.debug(f"Executing callback: {name}")
                
                # Execute the actual callback
                if inspect.iscoroutinefunction(metadata.callback):
                    result = await metadata.callback(context)
                else:
                    result = metadata.callback(context)
                
                # Log callback completion
                self.logger.debug(f"Callback {name} completed successfully")
                return result
                
            except Exception as e:
                self.logger.error(f"Callback {name} failed: {e}")
                raise
        
        return wrapper
    
    def _update_type_stats(self, callback_type: str, delta: int):
        """Update statistics for callback types."""
        if callback_type not in self.stats['callbacks_by_type']:
            self.stats['callbacks_by_type'][callback_type] = 0
        self.stats['callbacks_by_type'][callback_type] += delta
    
    def _update_priority_stats(self, priority: int, delta: int):
        """Update statistics for callback priorities."""
        if priority not in self.stats['callbacks_by_priority']:
            self.stats['callbacks_by_priority'][priority] = 0
        self.stats['callbacks_by_priority'][priority] += delta
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about callback registry."""
        return {
            **self.stats,
            'registered_callbacks': len(self.callbacks),
            'execution_history_length': len(self.execution_history),
            'currently_executing': list(self._executing_callbacks),
            'average_execution_time': round(self.stats['average_execution_time'], 3),
            'success_rate': (
                self.stats['successful_executions'] / max(1, self.stats['total_executions'])
                if self.stats['total_executions'] > 0 else 0
            )
        }
    
    def get_execution_history(self, 
                           limit: Optional[int] = None,
                           callback_name: Optional[str] = None,
                           success_only: bool = False) -> List[CallbackExecution]:
        """Get execution history with optional filtering."""
        history = self.execution_history
        
        if callback_name:
            history = [e for e in history if e.callback_name == callback_name]
        
        if success_only:
            history = [e for e in history if e.success]
        
        if limit:
            history = history[-limit:]
        
        return history
    
    def clear_execution_history(self):
        """Clear execution history."""
        self.execution_history.clear()
        self.logger.info("Execution history cleared")
    
    def export_configuration(self) -> Dict[str, Any]:
        """Export callback registry configuration."""
        return {
            'callbacks': {
                name: {
                    'type': metadata.callback_type.value,
                    'priority': metadata.priority.value,
                    'timeout': metadata.timeout,
                    'description': metadata.description,
                    'category': metadata.category,
                    'max_retries': metadata.max_retries,
                    'dependencies': metadata.dependencies,
                    'tags': metadata.tags
                }
                for name, metadata in self.callbacks.items()
            },
            'execution_plan': self.get_execution_plan(),
            'statistics': self.get_statistics()
        }


class CustomCallbackManager:
    """High-level manager for custom interrupt callbacks."""
    
    def __init__(self, interrupt_handler: InterruptHandler, config: InterruptConfig):
        self.interrupt_handler = interrupt_handler
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize registry
        self.registry = InterruptCallbackRegistry(interrupt_handler, config)
        
        # Predefined callback categories
        self.categories = {
            'cleanup': [],
            'data_preservation': [],
            'user_notification': [],
            'system': [],
            'custom': []
        }
    
    def register_cleanup_callback(self, 
                             name: str,
                             callback: Callable,
                             priority: CallbackPriority = CallbackPriority.HIGH,
                             timeout: Optional[float] = None,
                             **kwargs) -> bool:
        """Register a cleanup callback with convenience parameters."""
        return self.registry.register_callback(
            name=name,
            callback=callback,
            callback_type=CallbackType.CLEANUP,
            priority=priority,
            timeout=timeout,
            **kwargs
        )
    
    def register_data_preservation_callback(self, 
                                      name: str,
                                      callback: Callable,
                                      priority: CallbackPriority = CallbackPriority.CRITICAL,
                                      timeout: Optional[float] = None,
                                      **kwargs) -> bool:
        """Register a data preservation callback with convenience parameters."""
        return self.registry.register_callback(
            name=name,
            callback=callback,
            callback_type=CallbackType.DATA_PRESERVATION,
            priority=priority,
            timeout=timeout,
            **kwargs
        )
    
    def register_user_notification_callback(self, 
                                      name: str,
                                      callback: Callable,
                                      priority: CallbackPriority = CallbackPriority.NORMAL,
                                      timeout: Optional[float] = None,
                                      **kwargs) -> bool:
        """Register a user notification callback with convenience parameters."""
        return self.registry.register_callback(
            name=name,
            callback=callback,
            callback_type=CallbackType.USER_NOTIFICATION,
            priority=priority,
            timeout=timeout,
            **kwargs
        )
    
    def register_system_callback(self, 
                            name: str,
                            callback: Callable,
                            priority: CallbackPriority = CallbackPriority.LOW,
                            timeout: Optional[float] = None,
                            **kwargs) -> bool:
        """Register a system callback with convenience parameters."""
        return self.registry.register_callback(
            name=name,
            callback=callback,
            callback_type=CallbackType.SYSTEM,
            priority=priority,
            timeout=timeout,
            **kwargs
        )
    
    def get_callbacks_by_category(self, category: str) -> List[CallbackMetadata]:
        """Get all callbacks in a specific category."""
        callback_type_map = {
            'cleanup': CallbackType.CLEANUP,
            'data_preservation': CallbackType.DATA_PRESERVATION,
            'user_notification': CallbackType.USER_NOTIFICATION,
            'system': CallbackType.SYSTEM,
            'custom': CallbackType.CUSTOM
        }
        
        callback_type = callback_type_map.get(category)
        if callback_type:
            return self.registry.list_callbacks(callback_type=callback_type)
        
        return []
    
    def get_registry(self) -> InterruptCallbackRegistry:
        """Get the underlying registry for advanced operations."""
        return self.registry
