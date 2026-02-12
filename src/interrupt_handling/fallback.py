"""
Fallback mechanisms for interrupt handling when primary methods fail.
"""

import atexit
import logging
import sys
import os
import threading
import time
from typing import List, Callable, Optional, Dict, Any
from contextlib import contextmanager

from .config import InterruptConfig
from .resource_manager import ResourceManager
from .logging_utils import SignalSafeLogger


class FallbackHandler:
    """Provides fallback mechanisms for interrupt handling."""
    
    def __init__(self, config: InterruptConfig):
        self.config = config
        self.logger = SignalSafeLogger(__name__)
        self._cleanup_functions: List[Callable[[], None]] = []
        self._atexit_registered = False
        self._lock = threading.Lock()
        self._fallback_executed = False
        
        # Register atexit handler if enabled
        if self.config.enable_interrupt_handling:
            self._register_atexit_handler()
    
    def _register_atexit_handler(self):
        """Register atexit handler as fallback."""
        if self._atexit_registered:
            return
        
        try:
            atexit.register(self._atexit_cleanup)
            self._atexit_registered = True
            self.logger.debug("Registered atexit fallback handler")
        except Exception as e:
            self.logger.error(f"Failed to register atexit handler: {e}")
    
    def _atexit_cleanup(self):
        """Cleanup function called at program exit."""
        with self._lock:
            if self._fallback_executed:
                return  # Already executed
            
            self._fallback_executed = True
            self.logger.info("Executing atexit fallback cleanup")
            
            try:
                # Execute all registered cleanup functions
                for i, cleanup_func in enumerate(self._cleanup_functions):
                    try:
                        self.logger.debug(f"Executing fallback cleanup {i+1}/{len(self._cleanup_functions)}")
                        cleanup_func()
                    except Exception as e:
                        self.logger.error(f"Error in fallback cleanup {i+1}: {e}")
                
                self.logger.info("Atexit fallback cleanup completed")
                
            except Exception as e:
                self.logger.error(f"Critical error in atexit cleanup: {e}")
    
    def register_cleanup_function(self, cleanup_func: Callable[[], None]):
        """
        Register a cleanup function to be called as a fallback.
        
        This function will be called during atexit if primary interrupt
        handling fails or is not triggered.
        """
        with self._lock:
            self._cleanup_functions.append(cleanup_func)
            self.logger.debug(f"Registered fallback cleanup function: {cleanup_func.__name__}")
    
    def unregister_cleanup_function(self, cleanup_func: Callable[[], None]):
        """Unregister a cleanup function."""
        with self._lock:
            try:
                self._cleanup_functions.remove(cleanup_func)
                self.logger.debug(f"Unregistered fallback cleanup function: {cleanup_func.__name__}")
            except ValueError:
                self.logger.warning(f"Cleanup function not found for unregistration: {cleanup_func.__name__}")
    
    def execute_immediate_fallback(self):
        """Execute fallback cleanup immediately."""
        with self._lock:
            if self._fallback_executed:
                return
            
            self.logger.info("Executing immediate fallback cleanup")
            self._atexit_cleanup()
    
    def create_exception_handler(self, resource_manager: ResourceManager) -> Callable:
        """Create an exception handler that triggers fallback cleanup."""
        def exception_handler(exc_type, exc_value, exc_traceback):
            """Handle uncaught exceptions with fallback cleanup."""
            self.logger.error(f"Uncaught exception: {exc_type.__name__}: {exc_value}")
            
            # Execute fallback cleanup
            self.execute_immediate_fallback()
            
            # Call original exception handler if available
            if sys.__excepthook__:
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
        
        return exception_handler
    
    def setup_exception_handling(self, resource_manager: ResourceManager):
        """Setup global exception handling with fallback cleanup."""
        try:
            # Store original exception hook
            original_hook = sys.__excepthook__
            
            # Set new exception handler
            sys.excepthook = self.create_exception_handler(resource_manager)
            
            self.logger.debug("Setup global exception handler with fallback cleanup")
            return original_hook
            
        except Exception as e:
            self.logger.error(f"Failed to setup exception handling: {e}")
            return None
    
    def restore_exception_handling(self, original_hook: Optional[Callable]):
        """Restore original exception handling."""
        if original_hook:
            try:
                sys.excepthook = original_hook
                self.logger.debug("Restored original exception handler")
            except Exception as e:
                self.logger.error(f"Failed to restore exception handling: {e}")
    
    @contextmanager
    def fallback_context(self, resource_manager: Optional[ResourceManager] = None):
        """Context manager that ensures fallback cleanup."""
        original_hook = None
        
        try:
            # Setup exception handling if resource manager provided
            if resource_manager:
                original_hook = self.setup_exception_handling(resource_manager)
            
            yield
            
        except Exception as e:
            self.logger.error(f"Exception in fallback context: {e}")
            self.execute_immediate_fallback()
            raise
        finally:
            # Restore exception handling
            if original_hook:
                self.restore_exception_handling(original_hook)
    
    def create_signal_safe_decorator(self):
        """Create a decorator for signal-safe function execution."""
        def signal_safe(func):
            """Decorator that makes a function signal-safe."""
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except KeyboardInterrupt:
                    # Handle keyboard interrupt gracefully
                    self.logger.info("KeyboardInterrupt caught, executing fallback cleanup")
                    self.execute_immediate_fallback()
                    raise
                except Exception as e:
                    self.logger.error(f"Exception in signal-safe function {func.__name__}: {e}")
                    self.execute_immediate_fallback()
                    raise
            
            return wrapper
        return signal_safe
    
    def get_fallback_status(self) -> Dict[str, Any]:
        """Get fallback handler status."""
        with self._lock:
            return {
                'atexit_registered': self._atexit_registered,
                'cleanup_functions_count': len(self._cleanup_functions),
                'fallback_executed': self._fallback_executed,
                'interrupt_handling_enabled': self.config.enable_interrupt_handling
            }


class PeriodicCheckpointHandler:
    """Periodic checkpoint mechanism for data preservation."""
    
    def __init__(self, config: InterruptConfig):
        self.config = config
        self.logger = SignalSafeLogger(__name__)
        self._checkpoint_functions: List[Callable[[], None]] = []
        self._checkpoint_interval = 60.0  # Default 60 seconds
        self._timer_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
    
    def set_checkpoint_interval(self, interval: float):
        """Set the checkpoint interval in seconds."""
        with self._lock:
            self._checkpoint_interval = max(interval, 1.0)  # Minimum 1 second
            self.logger.debug(f"Checkpoint interval set to {self._checkpoint_interval}s")
    
    def register_checkpoint_function(self, checkpoint_func: Callable[[], None]):
        """Register a function to create checkpoints."""
        with self._lock:
            self._checkpoint_functions.append(checkpoint_func)
            self.logger.debug(f"Registered checkpoint function: {checkpoint_func.__name__}")
    
    def start_periodic_checkpoints(self):
        """Start periodic checkpoint creation."""
        with self._lock:
            if self._timer_thread and self._timer_thread.is_alive():
                return  # Already running
            
            self._stop_event.clear()
            self._timer_thread = threading.Thread(
                target=self._checkpoint_loop,
                name="periodic-checkpoint",
                daemon=True
            )
            self._timer_thread.start()
            self.logger.info(f"Started periodic checkpoints every {self._checkpoint_interval}s")
    
    def stop_periodic_checkpoints(self):
        """Stop periodic checkpoint creation."""
        with self._lock:
            if self._timer_thread and self._timer_thread.is_alive():
                self._stop_event.set()
                self._timer_thread.join(timeout=5.0)
                self.logger.info("Stopped periodic checkpoints")
    
    def _checkpoint_loop(self):
        """Main checkpoint loop."""
        while not self._stop_event.wait(self._checkpoint_interval):
            try:
                self._create_checkpoints()
            except Exception as e:
                self.logger.error(f"Error in periodic checkpoint: {e}")
    
    def _create_checkpoints(self):
        """Create checkpoints using all registered functions."""
        for i, checkpoint_func in enumerate(self._checkpoint_functions):
            try:
                self.logger.debug(f"Creating checkpoint {i+1}/{len(self._checkpoint_functions)}")
                checkpoint_func()
            except Exception as e:
                self.logger.error(f"Error in checkpoint function {i+1}: {e}")
    
    def create_immediate_checkpoint(self):
        """Create an immediate checkpoint."""
        self.logger.info("Creating immediate checkpoint")
        self._create_checkpoints()


# Global fallback handler instance
_fallback_handler = None


def get_fallback_handler(config: Optional[InterruptConfig] = None) -> FallbackHandler:
    """Get the global fallback handler instance."""
    global _fallback_handler
    if _fallback_handler is None:
        _fallback_handler = FallbackHandler(config or InterruptConfig())
    return _fallback_handler


def setup_fallback_mechanisms(config: InterruptConfig, resource_manager: ResourceManager):
    """Setup all fallback mechanisms."""
    fallback_handler = get_fallback_handler(config)
    
    # Register resource manager cleanup
    fallback_handler.register_cleanup_function(resource_manager.cleanup_all)
    
    # Setup exception handling
    fallback_handler.setup_exception_handling(resource_manager)
    
    # Setup periodic checkpoints if enabled
    if config.create_checkpoints:
        checkpoint_handler = PeriodicCheckpointHandler(config)
        checkpoint_handler.register_checkpoint_function(resource_manager.cleanup_all)
        checkpoint_handler.start_periodic_checkpoints()
    
    return fallback_handler
