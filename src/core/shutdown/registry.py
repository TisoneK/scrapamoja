"""
Cleanup registry for managing shutdown tasks with priority ordering.

Provides priority-based registration and execution of cleanup functions
with timeout protection and error handling.
"""

import asyncio
import time
from typing import Callable, List, Tuple, Any
from dataclasses import dataclass

from .exceptions import TimeoutError, ShutdownError
from .state import ShutdownState


@dataclass
class CleanupTask:
    """Represents a cleanup task with priority and metadata."""
    priority: int
    cleanup_fn: Callable
    name: str
    timeout_seconds: float = 15.0
    
    def __lt__(self, other: "CleanupTask") -> bool:
        """Enable priority queue sorting (lower priority = first execution)."""
        return self.priority < other.priority


class CleanupRegistry:
    """Registry for managing cleanup tasks with priority-based execution."""
    
    def __init__(self):
        self._tasks: List[CleanupTask] = []
        self._logger = None
    
    def set_logger(self, logger) -> None:
        """Set logger for registry operations."""
        self._logger = logger
    
    def register_cleanup(self, cleanup_fn: Callable, priority: int, name: str = None, timeout_seconds: float = 15.0) -> None:
        """Register a cleanup function with priority and timeout."""
        if name is None:
            name = getattr(cleanup_fn, '__name__', 'anonymous_cleanup')
        
        task = CleanupTask(
            priority=priority,
            cleanup_fn=cleanup_fn,
            name=name,
            timeout_seconds=timeout_seconds
        )
        
        self._tasks.append(task)
        self._tasks.sort()  # Maintain priority order
        
        if self._logger:
            self._logger.info("registered_cleanup_task", task_name=name, priority=priority, timeout_seconds=timeout_seconds)
    
    async def execute_all_cleanups(self) -> Tuple[int, int]:
        """Execute all registered cleanup tasks in priority order.
        
        Returns:
            Tuple of (successful_count, error_count)
        """
        if not self._tasks:
            if self._logger:
                self._logger.info("No cleanup tasks registered")
            return 0, 0
        
        successful_count = 0
        error_count = 0
        start_time = time.time()
        
        if self._logger:
            self._logger.info(f"Executing {len(self._tasks)} cleanup tasks")
        
        for task in self._tasks:
            try:
                task_start = time.time()
                if asyncio.iscoroutinefunction(task.cleanup_fn):
                    await asyncio.wait_for(task.cleanup_fn(), timeout=task.timeout_seconds)
                else:
                    # Run sync functions in thread pool to avoid blocking
                    await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(None, task.cleanup_fn),
                        timeout=task.timeout_seconds
                    )
                
                task_duration = time.time() - task_start
                successful_count += 1
                
                if self._logger:
                    self._logger.info(
                        "cleanup_completed", 
                        task_name=task.name, 
                        duration_seconds=f"{task_duration:.2f}s"
                    )
                    
            except asyncio.TimeoutError:
                error_count += 1
                if self._logger:
                    self._logger.error(
                        "cleanup_timeout", 
                        task_name=task.name, 
                        timeout_seconds=task.timeout_seconds
                    )
                    
            except Exception as e:
                error_count += 1
                if self._logger:
                    self._logger.error(
                        "cleanup_failed", 
                        task_name=task.name, 
                        error=str(e)
                    )
        
        total_duration = time.time() - start_time
        
        if self._logger:
            self._logger.info(
                "all_cleanups_completed",
                total_duration_seconds=f"{total_duration:.2f}s",
                successful_count=successful_count,
                error_count=error_count
            )
        
        return successful_count, error_count
    
    def get_task_count(self) -> int:
        """Get the number of registered cleanup tasks."""
        return len(self._tasks)
    
    def clear_tasks(self) -> None:
        """Clear all registered cleanup tasks."""
        self._tasks.clear()
        if self._logger:
            self._logger.info("Cleared all cleanup tasks")
