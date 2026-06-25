"""
Main shutdown coordinator for graceful application termination.

Provides centralized shutdown management with state tracking,
cleanup coordination, and metrics collection.
"""

import asyncio
import time
from typing import Optional

from .state import ShutdownState
from .registry import CleanupRegistry
from .handlers import SignalHandler
from .exceptions import ShutdownError


class ShutdownCoordinator:
    """Central coordinator for managing graceful shutdown lifecycle."""
    
    def __init__(self, default_timeout: float = 15.0):
        self._state = ShutdownState.RUNNING
        self._registry = CleanupRegistry()
        self._signal_handler: Optional[SignalHandler] = None
        self._default_timeout = default_timeout
        self._shutdown_start_time: Optional[float] = None
        self._shutdown_duration: Optional[float] = None
        self._logger = None
    
    def set_logger(self, logger) -> None:
        """Set logger for coordinator operations."""
        self._logger = logger
        self._registry.set_logger(logger)
        if self._signal_handler:
            self._signal_handler.set_logger(logger)
    
    def register_cleanup(self, cleanup_fn, priority: int, name: str = None, timeout_seconds: float = None) -> None:
        """Register a cleanup function with priority and optional timeout."""
        if timeout_seconds is None:
            timeout_seconds = self._default_timeout
        
        self._registry.register_cleanup(cleanup_fn, priority, name, timeout_seconds)
    
    def setup_signal_handlers(self) -> None:
        """Setup platform-specific signal handlers for graceful shutdown."""
        if self._signal_handler is None:
            self._signal_handler = SignalHandler(self.initiate_shutdown)
            self._signal_handler.set_logger(self._logger)
        
        self._signal_handler.register_signal_handlers()
    
    def is_shutting_down(self) -> bool:
        """Check if shutdown is in progress or completed."""
        return self._state.is_shutdown_in_progress()
    
    def get_state(self) -> ShutdownState:
        """Get current shutdown state."""
        return self._state
    
    def initiate_shutdown(self) -> None:
        """Initiate the shutdown process (can be called from signal handlers)."""
        if self._state == ShutdownState.RUNNING:
            self._state = ShutdownState.SHUTTING_DOWN
            self._shutdown_start_time = time.time()
            
            if self._logger:
                self._logger.info("shutdown_initiated")
        elif self._logger:
            self._logger.info("shutdown_already_in_progress", state=self._state.value)
    
    async def shutdown(self, timeout: float = None) -> bool:
        """Execute graceful shutdown with all registered cleanups.
        
        Args:
            timeout: Overall timeout for shutdown process
            
        Returns:
            True if shutdown completed successfully, False if errors occurred
        """
        if self._state == ShutdownState.COMPLETED:
            if self._logger:
                self._logger.info("shutdown_already_completed")
            return True
        
        # Initiate shutdown if not already started
        if self._state == ShutdownState.RUNNING:
            self.initiate_shutdown()
        
        try:
            if self._logger:
                self._logger.info("starting_graceful_shutdown")
            
            # Execute all cleanup tasks
            successful_count, error_count = await self._registry.execute_all_cleanups()
            
            # Calculate metrics
            if self._shutdown_start_time:
                self._shutdown_duration = time.time() - self._shutdown_start_time
            
            # Update state
            self._state = ShutdownState.COMPLETED
            
            # Log results
            if self._logger:
                self._logger.info(
                    "shutdown_completed",
                    duration_seconds=f"{self._shutdown_duration:.2f}s" if self._shutdown_duration else "unknown",
                    successful_count=successful_count,
                    error_count=error_count
                )
            
            return error_count == 0
            
        except Exception as e:
            self._state = ShutdownState.COMPLETED
            if self._logger:
                self._logger.error("shutdown_failed", error=str(e))
            raise ShutdownError("Shutdown failed", cause=e) from e
        
        finally:
            # Restore original signal handlers
            if self._signal_handler:
                self._signal_handler.restore_original_handlers()
    
    def get_metrics(self) -> dict:
        """Get shutdown metrics."""
        return {
            "state": self._state.value,
            "registered_tasks": self._registry.get_task_count(),
            "shutdown_duration": self._shutdown_duration,
            "shutdown_start_time": self._shutdown_start_time,
        }
    
    def reset(self) -> None:
        """Reset coordinator for testing purposes."""
        self._state = ShutdownState.RUNNING
        self._registry.clear_tasks()
        self._shutdown_start_time = None
        self._shutdown_duration = None
        
        if self._logger:
            self._logger.info("Shutdown coordinator reset")
