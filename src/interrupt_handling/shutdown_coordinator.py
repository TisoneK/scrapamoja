"""
Graceful shutdown coordination for interrupt handling.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from .handler import InterruptHandler, InterruptContext
from .resource_manager import ResourceManager
from .messaging import InterruptMessageHandler, MessageType
from .config import InterruptConfig


class ShutdownPhase(Enum):
    """Shutdown phase enumeration."""
    INITIATED = "initiated"
    ACKNOWLEDGED = "acknowledged"
    CRITICAL_OPERATIONS = "critical_operations"
    RESOURCE_CLEANUP = "resource_cleanup"
    DATA_PRESERVATION = "data_preservation"
    FINALIZATION = "finalization"
    COMPLETED = "completed"


@dataclass
class ShutdownTask:
    """Represents a shutdown task."""
    name: str
    phase: ShutdownPhase
    priority: int
    timeout: float
    callback: Callable
    dependencies: List[str] = None
    completed: bool = False
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error: Optional[Exception] = None


class ShutdownCoordinator:
    """Coordinates graceful shutdown of scraping operations."""
    
    def __init__(self, interrupt_handler: InterruptHandler, 
                 resource_manager: ResourceManager,
                 message_handler: InterruptMessageHandler,
                 config: InterruptConfig):
        self.interrupt_handler = interrupt_handler
        self.resource_manager = resource_manager
        self.message_handler = message_handler
        self.config = config
        
        self.logger = logging.getLogger(__name__)
        
        # Shutdown state
        self.current_phase = ShutdownPhase.INITIATED
        self.shutdown_start_time: Optional[float] = None
        self.shutdown_end_time: Optional[float] = None
        self.shutdown_tasks: Dict[str, ShutdownTask] = {}
        self.completed_tasks: List[str] = []
        self.failed_tasks: List[str] = []
        
        # Shutdown statistics
        self.shutdown_stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'total_duration': 0.0,
            'phase_durations': {}
        }
        
        # Register shutdown callback
        self.interrupt_handler.register_interrupt_callback(
            self._coordinate_shutdown
        )
    
    def register_shutdown_task(self, name: str, phase: ShutdownPhase,
                             priority: int = 0, timeout: Optional[float] = None,
                             callback: Callable = None, dependencies: List[str] = None):
        """Register a shutdown task."""
        if timeout is None:
            # Use phase-specific timeout from config
            timeout = self._get_phase_timeout(phase)
        
        task = ShutdownTask(
            name=name,
            phase=phase,
            priority=priority,
            timeout=timeout,
            callback=callback,
            dependencies=dependencies or []
        )
        
        self.shutdown_tasks[name] = task
        self.logger.debug(f"Registered shutdown task: {name} for phase {phase.value} (timeout: {timeout}s)")
    
    def _get_phase_timeout(self, phase: ShutdownPhase) -> float:
        """Get timeout for a specific shutdown phase from config."""
        timeouts = {
            ShutdownPhase.ACKNOWLEDGED: self.config.acknowledgment_timeout,
            ShutdownPhase.CRITICAL_OPERATIONS: self.config.critical_operations_timeout,
            ShutdownPhase.RESOURCE_CLEANUP: self.config.resource_cleanup_timeout,
            ShutdownPhase.DATA_PRESERVATION: self.config.data_preservation_timeout,
            ShutdownPhase.FINALIZATION: self.config.finalization_timeout,
            ShutdownPhase.COMPLETED: self.config.finalization_timeout,
        }
        return timeouts.get(phase, self.config.default_cleanup_timeout)
    
    async def _coordinate_shutdown(self, context: InterruptContext):
        """Coordinate the graceful shutdown process."""
        self.shutdown_start_time = time.time()
        self.message_handler.send_custom_message(
            "Initiating graceful shutdown...",
            MessageType.INFO
        )
        
        try:
            # Execute shutdown phases in order
            phases = [
                ShutdownPhase.ACKNOWLEDGED,
                ShutdownPhase.CRITICAL_OPERATIONS,
                ShutdownPhase.RESOURCE_CLEANUP,
                ShutdownPhase.DATA_PRESERVATION,
                ShutdownPhase.FINALIZATION,
                ShutdownPhase.COMPLETED
            ]
            
            for phase in phases:
                phase_start_time = time.time()
                self.current_phase = phase
                
                success = await self._execute_shutdown_phase(phase)
                
                phase_duration = time.time() - phase_start_time
                self.shutdown_stats['phase_durations'][phase.value] = phase_duration
                
                if not success:
                    self.logger.error(f"Shutdown phase {phase.value} failed")
                    break
            
            # Calculate final statistics
            self.shutdown_end_time = time.time()
            self.shutdown_stats['total_duration'] = (
                self.shutdown_end_time - self.shutdown_start_time
            )
            self.shutdown_stats['total_tasks'] = len(self.shutdown_tasks)
            self.shutdown_stats['completed_tasks'] = len(self.completed_tasks)
            self.shutdown_stats['failed_tasks'] = len(self.failed_tasks)
            
            # Report final status
            await self._report_shutdown_status()
            
        except Exception as e:
            self.logger.error(f"Error during shutdown coordination: {e}")
            self.message_handler.report_shutdown_error(e)
    
    async def _execute_shutdown_phase(self, phase: ShutdownPhase) -> bool:
        """Execute all tasks for a specific shutdown phase."""
        self.message_handler.send_custom_message(
            f"Executing shutdown phase: {phase.value}",
            MessageType.INFO
        )
        
        # Get tasks for this phase
        phase_tasks = [
            task for task in self.shutdown_tasks.values()
            if task.phase == phase
        ]
        
        # Sort by priority (higher priority first)
        phase_tasks.sort(key=lambda t: t.priority, reverse=True)
        
        # Execute tasks with timeout
        for task in phase_tasks:
            if not await self._execute_shutdown_task(task):
                return False
        
        return True
    
    async def _execute_shutdown_task(self, task: ShutdownTask) -> bool:
        """Execute a single shutdown task with timeout."""
        self.message_handler.report_progress(
            f"Shutdown task: {task.name}",
            len(self.completed_tasks),
            len(self.shutdown_tasks)
        )
        
        task.start_time = time.time()
        
        try:
            # Check dependencies
            if not self._check_task_dependencies(task):
                self.logger.warning(f"Skipping task {task.name} due to unmet dependencies")
                return True
            
            # Execute task with timeout
            if asyncio.iscoroutinefunction(task.callback):
                await asyncio.wait_for(task.callback(), timeout=task.timeout)
            else:
                task.callback()
            
            task.completed = True
            task.end_time = time.time()
            self.completed_tasks.append(task.name)
            
            self.logger.info(f"Shutdown task {task.name} completed successfully")
            return True
            
        except asyncio.TimeoutError:
            task.error = Exception(f"Task timed out after {task.timeout} seconds")
            self.failed_tasks.append(task.name)
            self.message_handler.report_cleanup_error(
                task.name, task.error, 1
            )
            return False
            
        except Exception as e:
            task.error = e
            self.failed_tasks.append(task.name)
            self.message_handler.report_cleanup_error(
                task.name, e, 1
            )
            return False
    
    def _check_task_dependencies(self, task: ShutdownTask) -> bool:
        """Check if all task dependencies are satisfied."""
        for dependency in task.dependencies:
            if dependency not in self.completed_tasks:
                return False
        return True
    
    async def _report_shutdown_status(self):
        """Report final shutdown status."""
        success = len(self.failed_tasks) == 0
        
        status_message = (
            f"Shutdown {'completed successfully' if success else 'completed with errors'}\n"
            f"Duration: {self.shutdown_stats['total_duration']:.2f} seconds\n"
            f"Tasks: {self.shutdown_stats['completed_tasks']}/{self.shutdown_stats['total_tasks']} completed"
        )
        
        if self.failed_tasks:
            status_message += f"\nFailed tasks: {', '.join(self.failed_tasks)}"
        
        self.message_handler.send_custom_message(
            status_message,
            MessageType.INFO if success else MessageType.WARNING
        )
    
    def get_shutdown_statistics(self) -> Dict[str, Any]:
        """Get detailed shutdown statistics."""
        return {
            'shutdown_stats': self.shutdown_stats.copy(),
            'completed_tasks': self.completed_tasks.copy(),
            'failed_tasks': self.failed_tasks.copy(),
            'task_details': {
                name: {
                    'phase': task.phase.value,
                    'priority': task.priority,
                    'completed': task.completed,
                    'duration': (
                        task.end_time - task.start_time
                        if task.start_time and task.end_time
                        else None
                    ),
                    'error': str(task.error) if task.error else None
                }
                for name, task in self.shutdown_tasks.items()
            }
        }
    
    def register_default_shutdown_tasks(self):
        """Register default shutdown tasks for common operations."""
        # Acknowledgment phase
        self.register_shutdown_task(
            "acknowledge_interrupt",
            ShutdownPhase.ACKNOWLEDGED,
            priority=100,
            callback=self._acknowledge_interrupt
        )
        
        # Critical operations phase
        self.register_shutdown_task(
            "complete_critical_operations",
            ShutdownPhase.CRITICAL_OPERATIONS,
            priority=100,
            callback=self._complete_critical_operations
        )
        
        # Resource cleanup phase
        self.register_shutdown_task(
            "cleanup_resources",
            ShutdownPhase.RESOURCE_CLEANUP,
            priority=100,
            callback=self._cleanup_resources
        )
        
        # Data preservation phase
        self.register_shutdown_task(
            "preserve_data",
            ShutdownPhase.DATA_PRESERVATION,
            priority=100,
            callback=self._preserve_data
        )
        
        # Finalization phase
        self.register_shutdown_task(
            "finalize_shutdown",
            ShutdownPhase.FINALIZATION,
            priority=100,
            callback=self._finalize_shutdown
        )
    
    async def _acknowledge_interrupt(self):
        """Acknowledge the interrupt signal."""
        self.message_handler.acknowledge_interrupt()
    
    async def _complete_critical_operations(self):
        """Complete or abort critical operations."""
        # This would be implemented by the specific scraper
        pass
    
    async def _cleanup_resources(self):
        """Cleanup all registered resources."""
        await self.resource_manager.cleanup_all()
    
    async def _preserve_data(self):
        """Preserve data through checkpoints and state saving."""
        # This would be implemented by the specific scraper
        pass
    
    async def _finalize_shutdown(self):
        """Finalize the shutdown process."""
        self.message_handler.send_custom_message(
            "Shutdown process finalized",
            MessageType.INFO
        )


class GracefulShutdownManager:
    """High-level manager for graceful shutdown operations."""
    
    def __init__(self, config: InterruptConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.interrupt_handler = InterruptHandler(config)
        self.resource_manager = ResourceManager(config)
        self.message_handler = InterruptMessageHandler(config)
        self.shutdown_coordinator = ShutdownCoordinator(
            self.interrupt_handler,
            self.resource_manager,
            self.message_handler,
            config
        )
        
        # Register default tasks
        self.shutdown_coordinator.register_default_shutdown_tasks()
    
    def register_custom_shutdown_task(self, name: str, phase: str,
                                    priority: int = 0, timeout: Optional[float] = None,
                                    callback: Callable = None, dependencies: List[str] = None):
        """Register a custom shutdown task."""
        phase_enum = ShutdownPhase(phase)
        self.shutdown_coordinator.register_shutdown_task(
            name, phase_enum, priority, timeout, callback, dependencies
        )
    
    def get_shutdown_statistics(self) -> Dict[str, Any]:
        """Get shutdown statistics."""
        return self.shutdown_coordinator.get_shutdown_statistics()
    
    def is_shutdown_in_progress(self) -> bool:
        """Check if shutdown is currently in progress."""
        return self.interrupt_handler.is_shutting_down()
    
    def get_current_shutdown_phase(self) -> str:
        """Get the current shutdown phase."""
        return self.shutdown_coordinator.current_phase.value
