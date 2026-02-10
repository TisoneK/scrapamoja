"""
Selector Engine Integration

Integrates resilience components with selector engine operations including
failure handling, retry mechanisms, and performance monitoring during selector resolution.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta

from ..retry.retry_manager import RetryManager, RetryPolicy
from ..checkpoint.checkpoint_manager import CheckpointManager, Checkpoint, CheckpointType
from ..resource.resource_manager import ResourceManager, Resource, ResourceType
from ..abort.abort_manager import AbortManager
from ..logging.resilience_logger import get_logger
from ..correlation import get_correlation_id
from ..events import publish_integration_event


class SelectorEngineIntegration:
    """Integrates resilience components with selector engine operations."""
    
    def __init__(self):
        """Initialize selector engine integration."""
        self.logger = get_logger("selector_engine_integration")
        
        # Component managers
        self.retry_manager: Optional[RetryManager] = None
        self.checkpoint_manager: Optional[CheckpointManager] = None
        self.resource_manager: Optional[ResourceManager] = None
        self.abort_manager: Optional[AbortManager] = None
        
        # Integration state
        self.selector_operations: Dict[str, Dict[str, Any]] = {}  # operation_id -> operation info
        self.selector_checkpoints: Dict[str, List[str]] = {}  # selector_id -> checkpoint_ids
        self.performance_metrics: Dict[str, List[Dict[str, Any]]] = {}  # selector_id -> metrics
        
        # Configuration
        self.auto_retry_enabled = True
        self.auto_checkpointing_enabled = True
        self.performance_monitoring_enabled = True
        self.default_retry_policy: Optional[RetryPolicy] = None
        
        # Callbacks
        self.operation_callbacks: List[Callable[[str, str, Dict[str, Any]], None]] = []
        
        # Integration state
        self._initialized = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def initialize(
        self,
        retry_manager: RetryManager,
        checkpoint_manager: CheckpointManager,
        resource_manager: ResourceManager,
        abort_manager: AbortManager
    ) -> None:
        """Initialize the integration with component managers."""
        if self._initialized:
            return
        
        self.retry_manager = retry_manager
        self.checkpoint_manager = checkpoint_manager
        self.resource_manager = resource_manager
        self.abort_manager = abort_manager
        
        # Create default retry policy for selector operations
        self.default_retry_policy = await self.retry_manager.create_retry_policy(
            name="selector_engine_default",
            backoff_type="exponential",
            max_attempts=3,
            base_delay_ms=1000,
            max_delay_ms=10000,
            jitter_type="full"
        )
        
        # Create resource for selector engine
        self.selector_resource_id = await self.resource_manager.create_resource(
            name="selector_engine",
            resource_type=ResourceType.CPU,
            description="Selector engine operations resource"
        )
        
        # Start monitoring task
        self._running = True
        self._monitoring_task = asyncio.create_task(self._integration_monitoring_loop())
        
        self._initialized = True
        
        self.logger.info(
            "Selector engine integration initialized",
            event_type="selector_engine_integration_initialized",
            correlation_id=get_correlation_id(),
            context={
                "auto_retry": self.auto_retry_enabled,
                "auto_checkpointing": self.auto_checkpointing_enabled,
                "performance_monitoring": self.performance_monitoring_enabled
            },
            component="selector_engine_integration"
        )
    
    async def shutdown(self) -> None:
        """Shutdown the integration gracefully."""
        if not self._initialized:
            return
        
        self._running = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Clean up resource
        if hasattr(self, 'selector_resource_id'):
            await self.resource_manager.delete_resource(self.selector_resource_id)
        
        self._initialized = False
        
        self.logger.info(
            "Selector engine integration shutdown",
            event_type="selector_engine_integration_shutdown",
            correlation_id=get_correlation_id(),
            component="selector_engine_integration"
        )
    
    async def execute_selector_operation(
        self,
        operation_id: str,
        selector: str,
        operation_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a selector operation with resilience integration.
        
        Args:
            operation_id: Unique operation identifier
            selector: CSS selector string
            operation_func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Operation result
        """
        if not self._initialized:
            return await operation_func(*args, **kwargs)
        
        start_time = time.time()
        
        try:
            # Record operation start
            self._record_operation_start(operation_id, selector)
            
            # Execute with retry if enabled
            if self.auto_retry_enabled:
                result = await self._execute_with_retry(
                    operation_id, selector, operation_func, *args, **kwargs
                )
            else:
                result = await operation_func(*args, **kwargs)
            
            # Record operation success
            execution_time = time.time() - start_time
            self._record_operation_success(operation_id, execution_time, result)
            
            # Record for abort evaluation
            await self.abort_manager.record_operation(
                operation_id=operation_id,
                success=True,
                response_time=execution_time
            )
            
            # Create checkpoint if enabled and operation was significant
            if self.auto_checkpointing_enabled and self._should_create_checkpoint(selector, result):
                await self._create_operation_checkpoint(operation_id, selector, result)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Record operation failure
            self._record_operation_failure(operation_id, execution_time, str(e))
            
            # Record for abort evaluation
            await self.abort_manager.record_operation(
                operation_id=operation_id,
                success=False,
                error_type=type(e).__name__,
                response_time=execution_time
            )
            
            # Re-raise the exception
            raise
    
    async def batch_selector_operations(
        self,
        operations: List[Dict[str, Any]]
    ) -> List[Any]:
        """
        Execute multiple selector operations with batch resilience.
        
        Args:
            operations: List of operation dictionaries
            
        Returns:
            List of results
        """
        if not self._initialized:
            # Execute without resilience
            results = []
            for op in operations:
                result = await op["func"](*op["args"], **op["kwargs"])
                results.append(result)
            return results
        
        # Create batch checkpoint
        batch_id = f"batch_{int(time.time())}"
        await self._create_batch_checkpoint(batch_id, operations)
        
        results = []
        failed_operations = []
        
        try:
            # Execute operations with concurrency control
            semaphore = asyncio.Semaphore(10)  # Limit concurrent operations
            
            async def execute_single_op(op):
                async with semaphore:
                    try:
                        result = await self.execute_selector_operation(
                            op["operation_id"],
                            op["selector"],
                            op["func"],
                            *op["args"],
                            **op["kwargs"]
                        )
                        return {"success": True, "result": result, "operation_id": op["operation_id"]}
                    except Exception as e:
                        failed_operations.append({"operation_id": op["operation_id"], "error": str(e)})
                        return {"success": False, "error": str(e), "operation_id": op["operation_id"]}
            
            # Execute all operations
            tasks = [execute_single_op(op) for op in operations]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in batch_results:
                if isinstance(result, Exception):
                    results.append({"success": False, "error": str(result)})
                else:
                    results.append(result)
            
            # Create final batch checkpoint
            await self._create_batch_result_checkpoint(batch_id, results, failed_operations)
            
            return results
            
        except Exception as e:
            self.logger.error(
                f"Batch selector operations failed: {str(e)}",
                event_type="batch_operations_error",
                correlation_id=get_correlation_id(),
                context={
                    "batch_id": batch_id,
                    "operation_count": len(operations),
                    "error": str(e)
                },
                component="selector_engine_integration"
            )
            raise
    
    async def get_selector_performance_metrics(self, selector: str) -> Dict[str, Any]:
        """Get performance metrics for a selector."""
        if selector not in self.performance_metrics:
            return {
                "selector": selector,
                "total_operations": 0,
                "success_rate": 0.0,
                "average_execution_time": 0.0,
                "error_count": 0
            }
        
        metrics = self.performance_metrics[selector]
        
        if not metrics:
            return {
                "selector": selector,
                "total_operations": 0,
                "success_rate": 0.0,
                "average_execution_time": 0.0,
                "error_count": 0
            }
        
        total_operations = len(metrics)
        successful_operations = len([m for m in metrics if m["success"]])
        success_rate = successful_operations / total_operations if total_operations > 0 else 0.0
        average_execution_time = sum(m["execution_time"] for m in metrics) / total_operations if total_operations > 0 else 0.0
        error_count = total_operations - successful_operations
        
        return {
            "selector": selector,
            "total_operations": total_operations,
            "success_rate": success_rate,
            "average_execution_time": average_execution_time,
            "error_count": error_count,
            "last_operation": metrics[-1]["timestamp"] if metrics else None
        }
    
    async def create_selector_checkpoint(
        self,
        selector: str,
        operation_data: Dict[str, Any],
        reason: str = "manual"
    ) -> Optional[str]:
        """Create a checkpoint for selector operations."""
        if not self._initialized:
            return None
        
        try:
            checkpoint = Checkpoint(
                job_id=f"selector_{selector}",
                sequence_number=len(self.selector_checkpoints.get(selector, [])) + 1,
                checkpoint_type=CheckpointType.MANUAL,
                description=f"Selector checkpoint: {reason}"
            )
            
            checkpoint_data = {
                "selector": selector,
                "operation_data": operation_data,
                "timestamp": datetime.utcnow().isoformat(),
                "reason": reason,
                "performance_metrics": await self.get_selector_performance_metrics(selector)
            }
            
            checkpoint_id = await self.checkpoint_manager.create_checkpoint(checkpoint, checkpoint_data)
            
            # Track checkpoint
            if selector not in self.selector_checkpoints:
                self.selector_checkpoints[selector] = []
            self.selector_checkpoints[selector].append(checkpoint_id)
            
            self.logger.info(
                f"Selector checkpoint created: {selector} - {reason}",
                event_type="selector_checkpoint_created",
                correlation_id=get_correlation_id(),
                context={
                    "selector": selector,
                    "checkpoint_id": checkpoint_id,
                    "reason": reason
                },
                component="selector_engine_integration"
            )
            
            return checkpoint_id
            
        except Exception as e:
            self.logger.error(
                f"Failed to create selector checkpoint for {selector}: {str(e)}",
                event_type="selector_checkpoint_error",
                correlation_id=get_correlation_id(),
                context={
                    "selector": selector,
                    "reason": reason,
                    "error": str(e)
                },
                component="selector_engine_integration"
            )
            return None
    
    def add_operation_callback(self, callback: Callable[[str, str, Dict[str, Any]], None]) -> None:
        """Add an operation callback."""
        self.operation_callbacks.append(callback)
    
    def remove_operation_callback(self, callback: Callable) -> bool:
        """Remove an operation callback."""
        if callback in self.operation_callbacks:
            self.operation_callbacks.remove(callback)
            return True
        return False
    
    def _record_operation_start(self, operation_id: str, selector: str) -> None:
        """Record the start of an operation."""
        self.selector_operations[operation_id] = {
            "selector": selector,
            "start_time": time.time(),
            "status": "running"
        }
    
    def _record_operation_success(self, operation_id: str, execution_time: float, result: Any) -> None:
        """Record a successful operation."""
        if operation_id in self.selector_operations:
            operation = self.selector_operations[operation_id]
            operation.update({
                "status": "success",
                "execution_time": execution_time,
                "end_time": time.time(),
                "result": str(result)[:100]  # Truncate large results
            })
            
            # Update performance metrics
            selector = operation["selector"]
            if selector not in self.performance_metrics:
                self.performance_metrics[selector] = []
            
            self.performance_metrics[selector].append({
                "timestamp": datetime.utcnow().isoformat(),
                "success": True,
                "execution_time": execution_time,
                "operation_id": operation_id
            })
            
            # Limit metrics history
            if len(self.performance_metrics[selector]) > 1000:
                self.performance_metrics[selector] = self.performance_metrics[selector][-1000:]
    
    def _record_operation_failure(self, operation_id: str, execution_time: float, error: str) -> None:
        """Record a failed operation."""
        if operation_id in self.selector_operations:
            operation = self.selector_operations[operation_id]
            operation.update({
                "status": "failed",
                "execution_time": execution_time,
                "end_time": time.time(),
                "error": error
            })
            
            # Update performance metrics
            selector = operation["selector"]
            if selector not in self.performance_metrics:
                self.performance_metrics[selector] = []
            
            self.performance_metrics[selector].append({
                "timestamp": datetime.utcnow().isoformat(),
                "success": False,
                "execution_time": execution_time,
                "error": error,
                "operation_id": operation_id
            })
            
            # Limit metrics history
            if len(self.performance_metrics[selector]) > 1000:
                self.performance_metrics[selector] = self.performance_metrics[selector][-1000:]
    
    async def _execute_with_retry(
        self,
        operation_id: str,
        selector: str,
        operation_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute operation with retry logic."""
        return await self.retry_manager.execute_with_retry(
            operation_func,
            self.default_retry_policy,
            operation_id=operation_id,
            selector=selector,
            *args,
            **kwargs
        )
    
    def _should_create_checkpoint(self, selector: str, result: Any) -> bool:
        """Determine if a checkpoint should be created."""
        # Create checkpoint for complex selectors or large results
        if len(selector) > 100:  # Complex selector
            return True
        
        if result and hasattr(result, '__len__') and len(result) > 100:  # Large result
            return True
        
        # Create checkpoint every 100 successful operations for a selector
        if selector in self.performance_metrics:
            metrics = self.performance_metrics[selector]
            successful_ops = [m for m in metrics if m["success"]]
            if len(successful_ops) % 100 == 0:
                return True
        
        return False
    
    async def _create_operation_checkpoint(self, operation_id: str, selector: str, result: Any) -> None:
        """Create a checkpoint for an operation."""
        operation = self.selector_operations.get(operation_id, {})
        
        await self.create_selector_checkpoint(
            selector=selector,
            operation_data={
                "operation_id": operation_id,
                "result": str(result)[:1000],  # Truncate large results
                "execution_time": operation.get("execution_time", 0),
                "timestamp": operation.get("end_time", datetime.utcnow().isoformat())
            },
            reason="operation_success"
        )
    
    async def _create_batch_checkpoint(self, batch_id: str, operations: List[Dict[str, Any]]) -> None:
        """Create a checkpoint for batch operations."""
        checkpoint = Checkpoint(
            job_id=f"batch_{batch_id}",
            sequence_number=1,
            checkpoint_type=CheckpointType.AUTO,
            description=f"Batch operations checkpoint: {batch_id}"
        )
        
        checkpoint_data = {
            "batch_id": batch_id,
            "operations": [
                {
                    "operation_id": op["operation_id"],
                    "selector": op["selector"]
                }
                for op in operations
            ],
            "timestamp": datetime.utcnow().isoformat(),
            "operation_count": len(operations)
        }
        
        await self.checkpoint_manager.create_checkpoint(checkpoint, checkpoint_data)
    
    async def _create_batch_result_checkpoint(
        self,
        batch_id: str,
        results: List[Any],
        failed_operations: List[Dict[str, Any]]
    ) -> None:
        """Create a checkpoint for batch results."""
        checkpoint = Checkpoint(
            job_id=f"batch_{batch_id}",
            sequence_number=2,
            checkpoint_type=CheckpointType.AUTO,
            description=f"Batch results checkpoint: {batch_id}"
        )
        
        checkpoint_data = {
            "batch_id": batch_id,
            "results": str(results)[:1000],  # Truncate large results
            "failed_operations": failed_operations,
            "timestamp": datetime.utcnow().isoformat(),
            "success_count": len([r for r in results if r.get("success", False)]),
            "failure_count": len(failed_operations)
        }
        
        await self.checkpoint_manager.create_checkpoint(checkpoint, checkpoint_data)
    
    async def _integration_monitoring_loop(self) -> None:
        """Main integration monitoring loop."""
        while self._running:
            try:
                # Clean up old operation records
                cutoff_time = time.time() - 3600  # 1 hour ago
                
                old_operations = [
                    op_id for op_id, op in self.selector_operations.items()
                    if op.get("end_time", 0) < cutoff_time
                ]
                
                for op_id in old_operations:
                    del self.selector_operations[op_id]
                
                await asyncio.sleep(300)  # Clean up every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    f"Error in selector engine monitoring loop: {str(e)}",
                    event_type="selector_engine_monitoring_loop_error",
                    correlation_id=get_correlation_id(),
                    context={"error": str(e)},
                    component="selector_engine_integration"
                )
                await asyncio.sleep(300)


# Global selector engine integration instance
_selector_engine_integration = SelectorEngineIntegration()


def get_selector_engine_integration() -> SelectorEngineIntegration:
    """Get the global selector engine integration instance."""
    return _selector_engine_integration
