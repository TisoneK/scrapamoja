"""
Flow execution system with priority handling and coordination.

This module provides utilities for executing flows with different priority levels,
supporting both sequential and parallel execution patterns.
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Type, Callable
from enum import Enum
import logging
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class FlowPriority(Enum):
    """Flow execution priority levels."""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


class FlowExecutionStatus(Enum):
    """Flow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class FlowExecution:
    """Flow execution result."""
    flow_name: str
    status: FlowExecutionStatus
    result: Any
    error: Optional[str]
    start_time: float
    end_time: float
    execution_time: float
    priority: FlowPriority
    dependencies: List[str]
    metadata: Dict[str, Any]


class FlowExecutor:
    """Advanced flow executor with priority handling and coordination."""
    
    def __init__(self, max_concurrent: int = 3):
        """
        Initialize flow executor.
        
        Args:
            max_concurrent: Maximum number of concurrent flow executions
        """
        self.max_concurrent = max_concurrent
        self.execution_queue = []
        self.running_executions = {}
        self.completed_executions = {}
        self.execution_history = []
        self.flow_dependencies = {}
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
    
    def set_flow_dependencies(self, dependencies: Dict[str, List[str]]) -> None:
        """
        Set flow dependencies for execution coordination.
        
        Args:
            dependencies: Dictionary mapping flow names to their dependencies
        """
        self.flow_dependencies = dependencies
        logger.info(f"Set flow dependencies for {len(dependencies)} flows")
    
    def validate_dependencies(self, flow_name: str, available_flows: List[str]) -> bool:
        """
        Validate that all dependencies for a flow are available.
        
        Args:
            flow_name: Name of the flow to validate
            available_flows: List of available flow names
            
        Returns:
            True if all dependencies are available
        """
        if flow_name not in self.flow_dependencies:
            return True  # No dependencies to validate
        
        dependencies = self.flow_dependencies[flow_name]
        for dep in dependencies:
            if dep not in available_flows:
                logger.error(f"Dependency '{dep}' for flow '{flow_name}' is not available")
                return False
        
        return True
    
    def calculate_execution_order(self, flows: List[str], priorities: Dict[str, FlowPriority] = None) -> List[str]:
        """
        Calculate optimal execution order based on dependencies and priorities.
        
        Args:
            flows: List of flow names to execute
            priorities: Optional priority mapping
            
        Returns:
            Ordered list of flow names for execution
        """
        if not flows:
            return []
        
        # Build dependency graph
        execution_order = []
        remaining_flows = set(flows)
        processed_flows = set()
        
        while remaining_flows:
            # Find flows with no unprocessed dependencies
            ready_flows = []
            for flow_name in remaining_flows:
                if flow_name not in processed_flows:
                    deps = self.flow_dependencies.get(flow_name, [])
                    if all(dep in processed_flows for dep in deps):
                        ready_flows.append(flow_name)
            
            if not ready_flows:
                logger.warning("Circular dependency detected or no ready flows")
                break
            
            # Sort ready flows by priority
            if priorities:
                ready_flows.sort(key=lambda f: priorities.get(f, FlowPriority.NORMAL).value)
            
            # Add ready flows to execution order
            for flow_name in ready_flows:
                execution_order.append(flow_name)
                processed_flows.add(flow_name)
                remaining_flows.discard(flow_name)
        
        return execution_order
    
    async def execute_flow(
        self, 
        flow_name: str, 
        flow_class: Type,
        *args, 
        priority: FlowPriority = FlowPriority.NORMAL,
        timeout: float = 30.0,
        dependencies: List[str] = None
    ) -> FlowExecution:
        """
        Execute a single flow with error handling and timeout.
        
        Args:
            flow_name: Name of the flow
            flow_class: Flow class to execute
            *args: Arguments to pass to flow execution
            priority: Execution priority
            timeout: Timeout in seconds
            dependencies: List of dependent flows
            
        Returns:
            FlowExecution result
        """
        start_time = time.time()
        
        # Check dependencies
        if dependencies:
            for dep in dependencies:
                if dep in self.completed_executions:
                    dep_result = self.completed_executions[dep]
                    if dep_result.status != FlowExecutionStatus.COMPLETED:
                        logger.error(f"Dependency '{dep}' failed for flow '{flow_name}'")
                        return FlowExecution(
                            flow_name=flow_name,
                            status=FlowExecutionStatus.FAILED,
                            error=f"Dependency '{dep}' failed: {dep_result.error}",
                            start_time=start_time,
                            end_time=time.time(),
                            execution_time=0,
                            priority=priority,
                            dependencies=dependencies or []
                        )
        
        # Validate dependencies
        available_flows = list(self.running_executions.keys()) + list(self.completed_executions.keys())
        if not self.validate_dependencies(flow_name, available_flows):
            return FlowExecution(
                flow_name=flow_name,
                status=FlowExecutionStatus.FAILED,
                error=f"Dependencies not available: {dependencies}",
                start_time=start_time,
                end_time=time.time(),
                execution_time=0,
                priority=priority,
                dependencies=dependencies or []
            )
        
        # Create execution instance
        try:
            flow_instance = flow_class()
            
            # Check if flow has async execute method
            if hasattr(flow_instance, 'execute') and asyncio.iscoroutinefunction(getattr(flow_instance, 'execute')):
                # Async execution
                execution = await asyncio.wait_for(
                    self._execute_async_flow(flow_instance, *args),
                    timeout=timeout
                )
            else:
                # Sync execution
                execution = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    self._execute_sync_flow,
                    flow_instance, *args
                )
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            return FlowExecution(
                flow_name=flow_name,
                status=FlowExecutionStatus.COMPLETED,
                result=execution,
                start_time=start_time,
                end_time=end_time,
                execution_time=execution_time,
                priority=priority,
                dependencies=dependencies or []
            )
            
        except asyncio.TimeoutError:
            logger.error(f"Flow '{flow_name}' execution timed out after {timeout}s")
            return FlowExecution(
                flow_name=flow_name,
                status=FlowExecutionStatus.TIMEOUT,
                error=f"Execution timed out after {timeout}s",
                start_time=start_time,
                end_time=time.time(),
                execution_time=timeout,
                priority=priority,
                dependencies=dependencies or []
            )
        
        except Exception as e:
            logger.error(f"Flow '{flow_name}' execution failed: {e}")
            return FlowExecution(
                flow_name=flow_name,
                status=FlowExecutionStatus.FAILED,
                error=str(e),
                start_time=start_time,
                end_time=time.time(),
                execution_time=time.time() - start_time,
                priority=priority,
                dependencies=dependencies or []
            )
    
    async def _execute_async_flow(self, flow_instance, *args):
        """Execute async flow method."""
        return await flow_instance.execute(*args)
    
    def _execute_sync_flow(self, flow_instance, *args):
        """Execute sync flow method."""
        if hasattr(flow_instance, 'execute'):
            return flow_instance.execute(*args)
        elif hasattr(flow_instance, 'run'):
            return flow_instance.run(*args)
        else:
            raise AttributeError(f"Flow instance has no execute or run method")
    
    async def execute_flows_sequential(
        self, 
        flow_names: List[str],
        flow_classes: Dict[str, Type],
        priorities: Dict[str, FlowPriority] = None
        **kwargs
    ) -> List[FlowExecution]:
        """
        Execute flows sequentially in dependency order.
        
        Args:
            flow_names: List of flow names to execute
            flow_classes: Dictionary of flow name -> flow class
            priorities: Optional priority mapping
            **kwargs: Additional keyword arguments
            
        Returns:
            List of flow execution results
        """
        execution_order = self.calculate_execution_order(flow_names, priorities)
        results = []
        
        for flow_name in execution_order:
            if flow_name in flow_classes:
                result = await self.execute_flow(
                    flow_name,
                    flow_classes[flow_name],
                    priority=priorities.get(flow_name, FlowPriority.NORMAL) if priorities else FlowPriority.NORMAL,
                    **kwargs
                )
                results.append(result)
            else:
                logger.warning(f"Flow '{flow_name}' not found in flow classes")
                results.append(FlowExecution(
                    flow_name=flow_name,
                    status=FlowExecutionStatus.FAILED,
                    error=f"Flow class not found",
                    start_time=time.time(),
                    end_time=time.time(),
                    execution_time=0,
                    priority=priorities.get(flow_name, FlowPriority.NORMAL) if priorities else FlowPriority.NORMAL,
                    dependencies=[]
                ))
        
        return results
    
    async def execute_flows_parallel(
        self,
        flow_names: List[str],
        flow_classes: Dict[str, Type],
        max_concurrent: int = None,
        **kwargs
    ) -> List[FlowExecution]:
        """
        Execute flows in parallel with concurrency control.
        
        Args:
            flow_names: List of flow names to execute
            flow_classes: Dictionary of flow name -> flow class
            max_concurrent: Maximum concurrent executions (defaults to instance max)
            **kwargs: Additional keyword arguments
            
        Returns:
            List of flow execution results
        """
        if max_concurrent is None:
            max_concurrent = self.max_concurrent
        
        # Filter available flows
        available_flows = {
            name: cls for name, cls in flow_classes.items()
            if name in flow_names
        }
        
        # Create execution tasks
        execution_tasks = []
        for flow_name in flow_names:
            if flow_name in available_flows:
                task = self.execute_flow(
                    flow_name,
                    available_flows[flow_name],
                    priority=FlowPriority.NORMAL,
                    **kwargs
                )
                execution_tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*execution_tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(FlowExecution(
                    flow_name=flow_names[i],
                    status=FlowExecutionStatus.FAILED,
                    error=str(result),
                    start_time=time.time(),
                    end_time=time.time(),
                    execution_time=0,
                    priority=FlowPriority.NORMAL,
                    dependencies=[]
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def execute_flows_with_priority(
        self,
        flow_configs: List[Dict[str, Any]],
        flow_classes: Dict[str, Type],
        **kwargs
    ) -> List[FlowExecution]:
        """
        Execute flows with priority-based scheduling.
        
        Args:
            flow_configs: List of flow configurations with name and priority
            flow_classes: Dictionary of flow name -> flow class
            **kwargs: Additional keyword arguments
            
        Returns:
            List of flow execution results
        """
        # Sort flows by priority
        sorted_configs = sorted(
            flow_configs,
            key=lambda config: config.get('priority', FlowPriority.NORMAL).value
        )
        
        # Execute in priority order
        results = []
        for config in sorted_configs:
            flow_name = config['name']
            if flow_name in flow_classes:
                result = await self.execute_flow(
                    flow_name,
                    flow_classes[flow_name],
                    priority=config.get('priority', FlowPriority.NORMAL),
                    **kwargs
                )
                results.append(result)
            else:
                logger.warning(f"Flow '{flow_name}' not found in flow classes")
                results.append(FlowExecution(
                    flow_name=flow_name,
                    status=FlowExecutionStatus.FAILED,
                    error=f"Flow class not found",
                    start_time=time.time(),
                    end_time=time.time(),
                    execution_time=0,
                    priority=config.get('priority', FlowPriority.NORMAL),
                    dependencies=[]
                ))
        
        return results
    
    def get_execution_summary(self, results: List[FlowExecution]) -> Dict[str, Any]:
        """
        Get execution summary statistics.
        
        Args:
            results: List of flow execution results
            
        Returns:
            Summary statistics
        """
        if not results:
            return {
                'total': 0,
                'completed': 0,
                'failed': 0,
                'timeout': 0,
                'cancelled': 0,
                'average_execution_time': 0,
                'total_execution_time': 0
            }
        
        status_counts = {}
        total_time = 0
        
        for result in results:
            status = result.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            total_time += result.execution_time
        
        return {
            'total': len(results),
            'status_breakdown': status_counts,
            'completed': status_counts.get('completed', 0),
            'failed': status_counts.get('failed', 0),
            'timeout': status_counts.get('timeout', 0),
            'cancelled': status_counts.get('cancelled', 0),
            'average_execution_time': total_time / len(results),
            'total_execution_time': total_time
        }
    
    def cancel_execution(self, flow_name: str) -> bool:
        """
        Cancel a running flow execution.
        
        Args:
            flow_name: Name of the flow to cancel
            
        Returns:
            True if cancelled, False if not found
        """
        if flow_name in self.running_executions:
            # Mark as cancelled
            execution = self.running_executions[flow_name]
            execution.status = FlowExecutionStatus.CANCELLED
            execution.end_time = time.time()
            
            # Remove from running executions
            del self.running_executions[flow_name]
            
            # Add to completed executions
            self.completed_executions[flow_name] = execution
            
            logger.info(f"Cancelled flow execution: {flow_name}")
            return True
        
        return False
    
    def get_execution_status(self, flow_name: str) -> Optional[FlowExecution]:
        """
        Get the current status of a flow execution.
        
        Args:
            flow_name: Name of the flow
            
        Returns:
            Current execution status or None
        """
        return self.running_executions.get(flow_name) or self.completed_executions.get(flow_name)
    
    def clear_history(self) -> None:
        """Clear execution history."""
        self.execution_history.clear()
        self.completed_executions.clear()
        self.running_executions.clear()
        logger.info("Cleared execution history")
    
    def export_execution_log(self, filename: str) -> None:
        """
        Export execution log to file for debugging.
        
        Args:
            filename: File to export execution log
        """
        try:
            log_data = {
                'execution_history': [
                    {
                        'flow_name': execution.flow_name,
                        'status': execution.status.value,
                        'execution_time': execution.execution_time,
                        'start_time': execution.start_time,
                        'end_time': execution.end_time,
                        'priority': execution.priority.value,
                        'dependencies': execution.dependencies,
                        'error': execution.error
                    }
                    for execution in self.execution_history
                ],
                'timestamp': time.time()
            }
            
            import json
            with open(filename, 'w') as f:
                json.dump(log_data, f, indent=2, default=str)
            
            logger.info(f"Exported execution log to {filename}")
            
        except Exception as e:
            logger.error(f"Failed to export execution log: {e}")


def create_flow_executor(max_concurrent: int = 3) -> FlowExecutor:
    """
    Convenience function to create a flow executor.
    
    Args:
        max_concurrent: Maximum number of concurrent executions
        
    Returns:
        FlowExecutor instance
    """
    return FlowExecutor(max_concurrent)
