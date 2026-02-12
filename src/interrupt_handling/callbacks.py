"""
Interrupt callback infrastructure for custom interrupt handling.
"""

import logging
import threading
from typing import Callable, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from .handler import InterruptContext


class CallbackPriority(Enum):
    """Priority levels for interrupt callbacks."""
    CRITICAL = 1    # System-critical operations (data preservation)
    HIGH = 2        # Important operations (resource cleanup)
    NORMAL = 3      # Standard operations (user notifications)
    LOW = 4         # Optional operations (analytics, logging)


@dataclass
class InterruptCallback:
    """A registered interrupt callback with metadata."""
    callback_func: Callable[[InterruptContext], None]
    priority: CallbackPriority
    name: str
    description: str = ""
    enabled: bool = True
    timeout: float = 5.0
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class CallbackRegistry:
    """Registry for managing interrupt callbacks."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._callbacks: List[InterruptCallback] = []
        self._lock = threading.RLock()
        
        # Statistics
        self._execution_count = 0
        self._execution_errors = 0
    
    def register_callback(
        self,
        callback_func: Callable[[InterruptContext], None],
        name: str,
        priority: CallbackPriority = CallbackPriority.NORMAL,
        description: str = "",
        timeout: float = 5.0,
        metadata: Optional[dict] = None
    ) -> bool:
        """
        Register an interrupt callback.
        
        Args:
            callback_func: Function to call when interrupt occurs
            name: Unique name for the callback
            priority: Execution priority
            description: Human-readable description
            timeout: Maximum execution time
            metadata: Additional metadata
            
        Returns:
            True if registration successful, False if name already exists
        """
        with self._lock:
            # Check for existing name
            if any(cb.name == name for cb in self._callbacks):
                self.logger.warning(f"Callback with name '{name}' already registered")
                return False
            
            callback = InterruptCallback(
                callback_func=callback_func,
                priority=priority,
                name=name,
                description=description,
                timeout=timeout,
                metadata=metadata or {}
            )
            
            self._callbacks.append(callback)
            self.logger.debug(f"Registered callback '{name}' with priority {priority.name}")
            return True
    
    def unregister_callback(self, name: str) -> bool:
        """
        Unregister a callback by name.
        
        Args:
            name: Name of callback to unregister
            
        Returns:
            True if unregistration successful, False if not found
        """
        with self._lock:
            for i, callback in enumerate(self._callbacks):
                if callback.name == name:
                    del self._callbacks[i]
                    self.logger.debug(f"Unregistered callback '{name}'")
                    return True
            
            self.logger.warning(f"Callback '{name}' not found for unregistration")
            return False
    
    def enable_callback(self, name: str) -> bool:
        """Enable a callback."""
        return self._set_callback_enabled(name, True)
    
    def disable_callback(self, name: str) -> bool:
        """Disable a callback."""
        return self._set_callback_enabled(name, False)
    
    def _set_callback_enabled(self, name: str, enabled: bool) -> bool:
        """Set callback enabled status."""
        with self._lock:
            for callback in self._callbacks:
                if callback.name == name:
                    callback.enabled = enabled
                    self.logger.debug(f"{'Enabled' if enabled else 'Disabled'} callback '{name}'")
                    return True
            
            self.logger.warning(f"Callback '{name}' not found")
            return False
    
    def execute_callbacks(self, context: InterruptContext) -> List[str]:
        """
        Execute all enabled callbacks in priority order.
        
        Args:
            context: Interrupt context information
            
        Returns:
            List of callback names that failed to execute
        """
        with self._lock:
            # Sort callbacks by priority (lower number = higher priority)
            sorted_callbacks = sorted(
                [cb for cb in self._callbacks if cb.enabled],
                key=lambda cb: cb.priority.value
            )
            
            failed_callbacks = []
            
            self.logger.debug(f"Executing {len(sorted_callbacks)} callbacks")
            
            for callback in sorted_callbacks:
                try:
                    self._execute_callback_with_timeout(callback, context)
                    self._execution_count += 1
                except Exception as e:
                    self._execution_errors += 1
                    failed_callbacks.append(callback.name)
                    self.logger.error(f"Error executing callback '{callback.name}': {e}")
            
            return failed_callbacks
    
    def _execute_callback_with_timeout(self, callback: InterruptCallback, context: InterruptContext):
        """Execute a callback with timeout protection."""
        import threading
        
        result_container = []
        error_container = []
        
        def target():
            try:
                callback.callback_func(context)
                result_container.append(True)
            except Exception as e:
                error_container.append(e)
        
        thread = threading.Thread(target=target, name=f"callback-{callback.name}")
        thread.start()
        thread.join(timeout=callback.timeout)
        
        if thread.is_alive():
            raise TimeoutError(f"Callback '{callback.name}' exceeded timeout of {callback.timeout}s")
        
        if error_container:
            raise error_container[0]
    
    def get_callback_info(self) -> List[dict]:
        """Get information about all registered callbacks."""
        with self._lock:
            return [
                {
                    'name': cb.name,
                    'priority': cb.priority.name,
                    'description': cb.description,
                    'enabled': cb.enabled,
                    'timeout': cb.timeout,
                    'metadata': cb.metadata
                }
                for cb in self._callbacks
            ]
    
    def get_statistics(self) -> dict:
        """Get callback execution statistics."""
        with self._lock:
            return {
                'total_callbacks': len(self._callbacks),
                'enabled_callbacks': len([cb for cb in self._callbacks if cb.enabled]),
                'execution_count': self._execution_count,
                'execution_errors': self._execution_errors,
                'success_rate': (
                    (self._execution_count - self._execution_errors) / max(self._execution_count, 1)
                ) * 100
            }


# Global callback registry instance
_callback_registry = CallbackRegistry()


def get_callback_registry() -> CallbackRegistry:
    """Get the global callback registry instance."""
    return _callback_registry


def interrupt_callback(
    name: str,
    priority: CallbackPriority = CallbackPriority.NORMAL,
    description: str = "",
    timeout: float = 5.0
):
    """
    Decorator for registering interrupt callbacks.
    
    Args:
        name: Unique name for the callback
        priority: Execution priority
        description: Human-readable description
        timeout: Maximum execution time
    """
    def decorator(func: Callable[[InterruptContext], None]):
        _callback_registry.register_callback(
            callback_func=func,
            name=name,
            priority=priority,
            description=description,
            timeout=timeout
        )
        return func
    
    return decorator
