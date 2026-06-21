"""
Selector Telemetry Integration

Integration layer for connecting telemetry system with the Selector Engine
providing seamless telemetry collection without modifying selector logic.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from contextlib import asynccontextmanager
import weakref

from ..interfaces import ISelectorTelemetryIntegration
from ..models import TelemetryEvent, PerformanceMetrics, QualityMetrics, StrategyMetrics, ErrorData, ContextData
from ..configuration.telemetry_config import TelemetryConfiguration
from ..utils import generate_correlation_id, TimingMeasurement
from ..exceptions import (
    TelemetryIntegrationError, TelemetryCollectionError,
    CorrelationIdError
)
from ..configuration.logging import get_logger


class SelectorTelemetryIntegration(ISelectorTelemetryIntegration):
    """
    Integration layer for telemetry system with Selector Engine.
    
    Provides seamless telemetry collection through event hooks and
    correlation tracking without modifying selector logic.
    """
    
    def __init__(self, config: TelemetryConfiguration, collector=None):
        """
        Initialize selector telemetry integration.
        
        Args:
            config: Telemetry configuration
            collector: Optional telemetry collector
        """
        self.config = config
        self.collector = collector
        self.logger = get_logger("selector_integration")
        
        # Integration state
        self._enabled = config.get("integration_enabled", True)
        self._hooks_enabled = config.get("selector_hooks_enabled", True)
        self._auto_registration = config.get("auto_registration", True)
        
        # Hook registry
        self._hooks: Dict[str, List[Callable]] = {
            "before_resolution": [],
            "after_resolution": [],
            "before_strategy": [],
            "after_strategy": [],
            "on_error": [],
            "on_performance": []
        }
        
        # Active operations tracking
        self._active_operations: Dict[str, Dict[str, Any]] = {}
        self._operations_lock = asyncio.Lock()
        
        # Correlation management
        self._correlation_contexts: Dict[str, Dict[str, Any]] = {}
        self._correlation_lock = asyncio.Lock()
        
        # Integration statistics
        self._integration_stats = {
            "operations_tracked": 0,
            "hooks_executed": 0,
            "correlation_ids_generated": 0,
            "integration_errors": 0,
            "start_time": datetime.utcnow()
        }
        
        # Performance tracking
        self._performance_measurements: Dict[str, TimingMeasurement] = {}
        
        # Initialize if auto-registration is enabled
        if self._auto_registration:
            asyncio.create_task(self._auto_register_hooks())
    
    async def initialize_integration(self, config: Dict[str, Any]) -> bool:
        """
        Initialize telemetry integration.
        
        Args:
            config: Integration configuration
            
        Returns:
            True if successfully initialized, False otherwise
            
        Raises:
            TelemetryIntegrationError: If initialization fails
        """
        try:
            # Update configuration
            self._enabled = config.get("enabled", True)
            self._hooks_enabled = config.get("hooks_enabled", True)
            
            # Validate collector
            if self.collector is None:
                self.logger.warning("No telemetry collector provided")
                return False
            
            # Test collector availability
            if hasattr(self.collector, 'is_enabled'):
                collector_enabled = await self.collector.is_enabled()
                if not collector_enabled:
                    self.logger.warning("Telemetry collector is disabled")
                    return False
            
            self.logger.info(
                "Selector telemetry integration initialized",
                enabled=self._enabled,
                hooks_enabled=self._hooks_enabled
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to initialize integration",
                error=str(e)
            )
            raise TelemetryIntegrationError(
                f"Failed to initialize integration: {e}",
                error_code="TEL-901",
                integration_point="initialization"
            )
    
    async def shutdown_integration(self) -> bool:
        """
        Shutdown telemetry integration.
        
        Returns:
            True if successfully shutdown, False otherwise
        """
        try:
            # Clear all hooks
            await self.clear_all_hooks()
            
            # Clear active operations
            async with self._operations_lock:
                self._active_operations.clear()
            
            # Clear correlation contexts
            async with self._correlation_lock:
                self._correlation_contexts.clear()
            
            # Clear performance measurements
            self._performance_measurements.clear()
            
            self.logger.info("Selector telemetry integration shutdown")
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to shutdown integration",
                error=str(e)
            )
            return False
    
    async def register_selector_hook(
        self,
        selector_name: str,
        hook_type: str,
        callback: Callable
    ) -> bool:
        """
        Register a hook for selector operations.
        
        Args:
            selector_name: Name of selector
            hook_type: Type of hook (before, after, error)
            callback: Hook callback function
            
        Returns:
            True if successfully registered, False otherwise
            
        Raises:
            TelemetryIntegrationError: If registration fails
        """
        try:
            if hook_type not in self._hooks:
                raise TelemetryIntegrationError(
                    f"Invalid hook type: {hook_type}",
                    error_code="TEL-902",
                    integration_point="hook_registration"
                )
            
            # Add hook to registry
            self._hooks[hook_type].append({
                "selector_name": selector_name,
                "callback": callback,
                "registered_at": datetime.utcnow()
            })
            
            self.logger.debug(
                "Hook registered",
                selector_name=selector_name,
                hook_type=hook_type
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to register hook",
                selector_name=selector_name,
                hook_type=hook_type,
                error=str(e)
            )
            raise TelemetryIntegrationError(
                f"Failed to register hook: {e}",
                error_code="TEL-903",
                integration_point="hook_registration"
            )
    
    async def unregister_selector_hook(
        self,
        selector_name: str,
        hook_type: str
    ) -> bool:
        """
        Unregister a selector hook.
        
        Args:
            selector_name: Name of selector
            hook_type: Type of hook
            
        Returns:
            True if successfully unregistered, False otherwise
        """
        try:
            if hook_type not in self._hooks:
                return False
            
            # Remove hooks for selector
            original_count = len(self._hooks[hook_type])
            self._hooks[hook_type] = [
                hook for hook in self._hooks[hook_type]
                if hook["selector_name"] != selector_name
            ]
            
            removed_count = original_count - len(self._hooks[hook_type])
            
            self.logger.debug(
                "Hooks unregistered",
                selector_name=selector_name,
                hook_type=hook_type,
                removed_count=removed_count
            )
            
            return removed_count > 0
            
        except Exception as e:
            self.logger.error(
                "Failed to unregister hook",
                selector_name=selector_name,
                hook_type=hook_type,
                error=str(e)
            )
            return False
    
    async def on_selector_resolution_start(
        self,
        selector_name: str,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Called when selector resolution starts.
        
        Args:
            selector_name: Name of selector
            correlation_id: Optional correlation ID
            **kwargs: Additional context
            
        Returns:
            Event ID for tracking
        """
        if not self._enabled or not self._hooks_enabled:
            return ""
        
        try:
            # Generate correlation ID if not provided
            if not correlation_id:
                correlation_id = generate_correlation_id()
                async with self._correlation_lock:
                    self._integration_stats["correlation_ids_generated"] += 1
            
            # Create event ID
            event_id = f"resolution_start_{int(time.time() * 1000)}"
            
            # Start performance measurement
            measurement = TimingMeasurement(
                start_time=datetime.utcnow(),
                operation_type="resolution",
                correlation_id=correlation_id,
                metadata={"selector_name": selector_name}
            )
            self._performance_measurements[event_id] = measurement
            
            # Track operation
            async with self._operations_lock:
                self._active_operations[event_id] = {
                    "selector_name": selector_name,
                    "operation_type": "resolution",
                    "correlation_id": correlation_id,
                    "start_time": datetime.utcnow(),
                    "context": kwargs
                }
                self._integration_stats["operations_tracked"] += 1
            
            # Execute before_resolution hooks
            await self._execute_hooks("before_resolution", {
                "selector_name": selector_name,
                "correlation_id": correlation_id,
                "event_id": event_id,
                "context": kwargs
            })
            
            self.logger.debug(
                "Selector resolution started",
                selector_name=selector_name,
                correlation_id=correlation_id,
                event_id=event_id
            )
            
            return event_id
            
        except Exception as e:
            self._integration_stats["integration_errors"] += 1
            self.logger.error(
                "Failed to handle resolution start",
                selector_name=selector_name,
                error=str(e)
            )
            return ""
    
    async def on_selector_resolution_complete(
        self,
        event_id: str,
        selector_name: str,
        success: bool,
        confidence_score: Optional[float] = None,
        elements_found: Optional[int] = None,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        Called when selector resolution completes.
        
        Args:
            event_id: Event ID from start
            selector_name: Name of selector
            success: Whether resolution was successful
            confidence_score: Confidence score if available
            elements_found: Number of elements found
            correlation_id: Optional correlation ID
            **kwargs: Additional context
            
        Returns:
            True if event recorded successfully
        """
        if not self._enabled or not self._hooks_enabled or not event_id:
            return False
        
        try:
            # Finish performance measurement
            measurement = self._performance_measurements.get(event_id)
            if measurement:
                measurement.finish()
                performance_metrics = {
                    "resolution_time_ms": measurement.get_duration_ms(),
                    "total_duration_ms": measurement.get_duration_ms()
                }
            else:
                performance_metrics = {}
            
            # Create quality metrics
            quality_metrics = {
                "success": success,
                "confidence_score": confidence_score,
                "elements_found": elements_found
            }
            
            # Remove None values
            quality_metrics = {k: v for k, v in quality_metrics.items() if v is not None}
            
            # Create telemetry event
            if self.collector:
                await self.collector.collect_event(
                    selector_name=selector_name,
                    operation_type="resolution",
                    correlation_id=correlation_id,
                    performance_metrics=performance_metrics,
                    quality_metrics=quality_metrics,
                    context_data=kwargs.get("context_data")
                )
            
            # Execute after_resolution hooks
            await self._execute_hooks("after_resolution", {
                "selector_name": selector_name,
                "correlation_id": correlation_id,
                "event_id": event_id,
                "success": success,
                "confidence_score": confidence_score,
                "elements_found": elements_found,
                "performance_metrics": performance_metrics,
                "context": kwargs
            })
            
            # Clean up tracking
            await self._cleanup_operation(event_id)
            
            self.logger.debug(
                "Selector resolution completed",
                selector_name=selector_name,
                correlation_id=correlation_id,
                success=success,
                confidence_score=confidence_score
            )
            
            return True
            
        except Exception as e:
            self._integration_stats["integration_errors"] += 1
            self.logger.error(
                "Failed to handle resolution complete",
                selector_name=selector_name,
                error=str(e)
            )
            return False
    
    async def on_strategy_execution_start(
        self,
        event_id: str,
        strategy_name: str,
        selector_name: str,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Called when strategy execution starts.
        
        Args:
            event_id: Event ID
            strategy_name: Name of strategy
            selector_name: Name of selector
            correlation_id: Optional correlation ID
            **kwargs: Additional context
        """
        if not self._enabled or not self._hooks_enabled:
            return
        
        try:
            # Start strategy performance measurement
            strategy_event_id = f"strategy_{event_id}_{strategy_name}"
            measurement = TimingMeasurement(
                start_time=datetime.utcnow(),
                operation_type="strategy",
                correlation_id=correlation_id,
                metadata={
                    "selector_name": selector_name,
                    "strategy_name": strategy_name
                }
            )
            self._performance_measurements[strategy_event_id] = measurement
            
            # Execute before_strategy hooks
            await self._execute_hooks("before_strategy", {
                "selector_name": selector_name,
                "strategy_name": strategy_name,
                "correlation_id": correlation_id,
                "event_id": event_id,
                "strategy_event_id": strategy_event_id,
                "context": kwargs
            })
            
            self.logger.debug(
                "Strategy execution started",
                strategy_name=strategy_name,
                selector_name=selector_name,
                correlation_id=correlation_id
            )
            
        except Exception as e:
            self._integration_stats["integration_errors"] += 1
            self.logger.error(
                "Failed to handle strategy start",
                strategy_name=strategy_name,
                error=str(e)
            )
    
    async def on_strategy_execution_complete(
        self,
        event_id: str,
        strategy_name: str,
        success: bool,
        execution_time_ms: float,
        selector_name: str,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Called when strategy execution completes.
        
        Args:
            event_id: Event ID
            strategy_name: Name of strategy
            success: Whether strategy was successful
            execution_time_ms: Execution time in milliseconds
            selector_name: Name of selector
            correlation_id: Optional correlation ID
            **kwargs: Additional context
        """
        if not self._enabled or not self._hooks_enabled:
            return
        
        try:
            # Finish strategy performance measurement
            strategy_event_id = f"strategy_{event_id}_{strategy_name}"
            measurement = self._performance_measurements.get(strategy_event_id)
            
            if measurement:
                measurement.finish()
                actual_time = measurement.get_duration_ms()
            else:
                actual_time = execution_time_ms
            
            # Create strategy metrics
            strategy_metrics = {
                "primary_strategy": strategy_name,
                "strategy_execution_time_ms": actual_time,
                "strategy_success_by_type": {strategy_name: success}
            }
            
            # Execute after_strategy hooks
            await self._execute_hooks("after_strategy", {
                "selector_name": selector_name,
                "strategy_name": strategy_name,
                "correlation_id": correlation_id,
                "event_id": event_id,
                "success": success,
                "execution_time_ms": actual_time,
                "strategy_metrics": strategy_metrics,
                "context": kwargs
            })
            
            # Clean up measurement
            if strategy_event_id in self._performance_measurements:
                del self._performance_measurements[strategy_event_id]
            
            self.logger.debug(
                "Strategy execution completed",
                strategy_name=strategy_name,
                selector_name=selector_name,
                success=success,
                execution_time_ms=actual_time
            )
            
        except Exception as e:
            self._integration_stats["integration_errors"] += 1
            self.logger.error(
                "Failed to handle strategy complete",
                strategy_name=strategy_name,
                error=str(e)
            )
    
    async def on_selector_error(
        self,
        event_id: str,
        selector_name: str,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        Called when selector operation encounters an error.
        
        Args:
            event_id: Event ID
            selector_name: Name of selector
            error_type: Type of error
            error_message: Error message
            stack_trace: Optional stack trace
            correlation_id: Optional correlation ID
            **kwargs: Additional context
            
        Returns:
            True if error recorded successfully
        """
        if not self._enabled or not self._hooks_enabled:
            return False
        
        try:
            # Create error data
            error_data = {
                "error_type": error_type,
                "error_message": error_message,
                "stack_trace": stack_trace
            }
            
            # Create telemetry event for error
            if self.collector:
                await self.collector.collect_event(
                    selector_name=selector_name,
                    operation_type="resolution",
                    correlation_id=correlation_id,
                    error_data=error_data,
                    context_data=kwargs.get("context_data")
                )
            
            # Execute error hooks
            await self._execute_hooks("on_error", {
                "selector_name": selector_name,
                "correlation_id": correlation_id,
                "event_id": event_id,
                "error_type": error_type,
                "error_message": error_message,
                "stack_trace": stack_trace,
                "context": kwargs
            })
            
            # Clean up tracking
            await self._cleanup_operation(event_id)
            
            self.logger.warning(
                "Selector error recorded",
                selector_name=selector_name,
                error_type=error_type,
                correlation_id=correlation_id
            )
            
            return True
            
        except Exception as e:
            self._integration_stats["integration_errors"] += 1
            self.logger.error(
                "Failed to handle selector error",
                selector_name=selector_name,
                error_type=error_type,
                error=str(e)
            )
            return False
    
    async def on_selector_performance_update(
        self,
        event_id: str,
        selector_name: str,
        metric_name: str,
        metric_value: float,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Called when selector performance metric is updated.
        
        Args:
            event_id: Event ID
            selector_name: Name of selector
            metric_name: Name of metric
            metric_value: Metric value
            correlation_id: Optional correlation ID
            **kwargs: Additional context
        """
        if not self._enabled or not self._hooks_enabled:
            return
        
        try:
            # Execute performance hooks
            await self._execute_hooks("on_performance", {
                "selector_name": selector_name,
                "correlation_id": correlation_id,
                "event_id": event_id,
                "metric_name": metric_name,
                "metric_value": metric_value,
                "context": kwargs
            })
            
            self.logger.debug(
                "Performance metric updated",
                selector_name=selector_name,
                metric_name=metric_name,
                metric_value=metric_value
            )
            
        except Exception as e:
            self._integration_stats["integration_errors"] += 1
            self.logger.error(
                "Failed to handle performance update",
                selector_name=selector_name,
                metric_name=metric_name,
                error=str(e)
            )
    
    async def get_correlation_id(self, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate or get correlation ID for operation tracking.
        
        Args:
            context: Optional context for correlation ID generation
            
        Returns:
            Correlation ID
        """
        try:
            correlation_id = generate_correlation_id(context=context)
            
            async with self._correlation_lock:
                self._correlation_contexts[correlation_id] = {
                    "created_at": datetime.utcnow(),
                    "context": context or {}
                }
                self._integration_stats["correlation_ids_generated"] += 1
            
            return correlation_id
            
        except Exception as e:
            raise CorrelationIdError(
                f"Failed to generate correlation ID: {e}",
                operation="get_correlation_id"
            )
    
    async def start_operation_session(
        self,
        session_id: str,
        operation_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Start a telemetry session for an operation.
        
        Args:
            session_id: Unique session identifier
            operation_type: Type of operation
            context: Optional session context
        """
        try:
            async with self._operations_lock:
                self._active_operations[session_id] = {
                    "operation_type": operation_type,
                    "start_time": datetime.utcnow(),
                    "context": context or {},
                    "events": []
                }
            
            self.logger.debug(
                "Operation session started",
                session_id=session_id,
                operation_type=operation_type
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to start operation session",
                session_id=session_id,
                error=str(e)
            )
    
    async def end_operation_session(
        self,
        session_id: str,
        success: bool,
        summary: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        End a telemetry session and get session summary.
        
        Args:
            session_id: Session identifier
            success: Whether operation was successful
            summary: Optional session summary
            
        Returns:
            Session statistics and summary
        """
        try:
            async with self._operations_lock:
                if session_id not in self._active_operations:
                    raise TelemetryIntegrationError(
                        f"Session {session_id} not found",
                        error_code="TEL-904",
                        integration_point="session_management"
                    )
                
                session = self._active_operations.pop(session_id)
                session["end_time"] = datetime.utcnow()
                session["duration_ms"] = (
                    session["end_time"] - session["start_time"]
                ).total_seconds() * 1000
                session["success"] = success
                session["summary"] = summary or {}
                session["event_count"] = len(session["events"])
            
            self.logger.info(
                "Operation session ended",
                session_id=session_id,
                success=success,
                duration_ms=session["duration_ms"],
                event_count=session["event_count"]
            )
            
            return session
            
        except Exception as e:
            self.logger.error(
                "Failed to end operation session",
                session_id=session_id,
                error=str(e)
            )
            raise
    
    async def get_active_sessions(self) -> List[Dict[str, Any]]:
        """
        Get list of active telemetry sessions.
        
        Returns:
            List of active session information
        """
        async with self._operations_lock:
            return [
                {
                    "session_id": session_id,
                    "operation_type": session["operation_type"],
                    "start_time": session["start_time"],
                    "duration_ms": (
                        datetime.utcnow() - session["start_time"]
                    ).total_seconds() * 1000,
                    "event_count": len(session["events"])
                }
                for session_id, session in self._active_operations.items()
            ]
    
    async def is_integration_enabled(self) -> bool:
        """
        Check if telemetry integration is enabled.
        
        Returns:
            True if integration is enabled
        """
        return self._enabled
    
    async def enable_integration(self) -> None:
        """
        Enable telemetry integration.
        """
        self._enabled = True
        self.logger.info("Telemetry integration enabled")
    
    async def disable_integration(self) -> None:
        """
        Disable telemetry integration.
        """
        self._enabled = False
        self.logger.info("Telemetry integration disabled")
    
    async def get_integration_statistics(self) -> Dict[str, Any]:
        """
        Get integration statistics.
        
        Returns:
            Integration statistics including events captured, hooks registered, etc.
        """
        runtime = datetime.utcnow() - self._integration_stats["start_time"]
        
        return {
            **self._integration_stats,
            "runtime_seconds": runtime.total_seconds(),
            "hooks_registered": sum(len(hooks) for hooks in self._hooks.values()),
            "active_operations": len(self._active_operations),
            "active_correlations": len(self._correlation_contexts),
            "performance_measurements": len(self._performance_measurements),
            "enabled": self._enabled,
            "hooks_enabled": self._hooks_enabled
        }
    
    async def get_integration_health(self) -> Dict[str, Any]:
        """
        Get integration health status.
        
        Returns:
            Health status information
        """
        try:
            stats = await self.get_integration_statistics()
            
            # Calculate health metrics
            error_rate = (
                stats["integration_errors"] / max(1, stats["operations_tracked"])
            )
            
            # Determine health status
            if error_rate > 0.1:  # > 10% error rate
                health_status = "unhealthy"
            elif error_rate > 0.05:  # > 5% error rate
                health_status = "warning"
            else:
                health_status = "healthy"
            
            return {
                "status": health_status,
                "error_rate": error_rate,
                "enabled": stats["enabled"],
                "hooks_enabled": stats["hooks_enabled"],
                "active_operations": stats["active_operations"],
                "last_activity": self._integration_stats["start_time"]
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def configure_integration(self, config: Dict[str, Any]) -> None:
        """
        Configure integration settings.
        
        Args:
            config: Integration configuration
        """
        if "enabled" in config:
            self._enabled = config["enabled"]
        
        if "hooks_enabled" in config:
            self._hooks_enabled = config["hooks_enabled"]
        
        self.logger.info("Integration configuration updated")
    
    async def test_integration(self) -> Dict[str, Any]:
        """
        Test integration functionality.
        
        Returns:
            Test results
        """
        test_results = {
            "correlation_id_generation": False,
            "hook_registration": False,
            "operation_tracking": False,
            "performance_measurement": False,
            "overall": False
        }
        
        try:
            # Test correlation ID generation
            correlation_id = await self.get_correlation_id()
            test_results["correlation_id_generation"] = bool(correlation_id)
            
            # Test hook registration
            test_callback = lambda x: None
            await self.register_selector_hook("test_selector", "before_resolution", test_callback)
            test_results["hook_registration"] = True
            
            # Test operation tracking
            await self.start_operation_session("test_session", "test_operation")
            session = await self.end_operation_session("test_session", True)
            test_results["operation_tracking"] = session["success"]
            
            # Test performance measurement
            from ..utils import start_timing, finish_timing
            measurement_id = start_timing("test_measurement")
            measurement = finish_timing(measurement_id)
            test_results["performance_measurement"] = measurement.is_finished()
            
            # Clean up test hook
            await self.unregister_selector_hook("test_selector", "before_resolution")
            
            # Overall test result
            test_results["overall"] = all(test_results.values())
            
        except Exception as e:
            self.logger.error(
                "Integration test failed",
                error=str(e)
            )
            test_results["error"] = str(e)
        
        return test_results
    
    async def get_registered_hooks(self) -> List[Dict[str, Any]]:
        """
        Get list of registered hooks.
        
        Returns:
            List of registered hook information
        """
        hooks_info = []
        
        for hook_type, hooks in self._hooks.items():
            for hook_info in hooks:
                hooks_info.append({
                    "hook_type": hook_type,
                    "selector_name": hook_info["selector_name"],
                    "registered_at": hook_info["registered_at"],
                    "callback_name": hook_info["callback"].__name__
                })
        
        return hooks_info
    
    async def clear_all_hooks(self) -> bool:
        """
        Clear all registered hooks.
        
        Returns:
            True if hooks cleared successfully
        """
        try:
            total_hooks = sum(len(hooks) for hooks in self._hooks.values())
            
            for hook_type in self._hooks:
                self._hooks[hook_type].clear()
            
            self.logger.info(
                "All hooks cleared",
                total_hooks=total_hooks
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to clear hooks",
                error=str(e)
            )
            return False
    
    # Private methods
    
    async def _execute_hooks(self, hook_type: str, context: Dict[str, Any]) -> None:
        """Execute hooks of a specific type."""
        if hook_type not in self._hooks:
            return
        
        for hook_info in self._hooks[hook_type]:
            try:
                await hook_info["callback"](context)
                self._integration_stats["hooks_executed"] += 1
            except Exception as e:
                self.logger.warning(
                    "Hook execution failed",
                    hook_type=hook_type,
                    selector_name=hook_info["selector_name"],
                    error=str(e)
                )
    
    async def _cleanup_operation(self, event_id: str) -> None:
        """Clean up operation tracking."""
        # Remove from active operations
        async with self._operations_lock:
            if event_id in self._active_operations:
                del self._active_operations[event_id]
        
        # Remove performance measurement
        if event_id in self._performance_measurements:
            del self._performance_measurements[event_id]
    
    async def _auto_register_hooks(self) -> None:
        """Auto-register hooks with selector engine if available."""
        try:
            # This would integrate with the actual selector engine
            # For now, we'll just log that auto-registration was attempted
            self.logger.info("Auto-registration attempted (selector engine integration needed)")
            
        except Exception as e:
            self.logger.warning(
                "Auto-registration failed",
                error=str(e)
            )


# Decorators for easy integration

def track_selector_resolution(selector_name: str = None):
    """
    Decorator to track selector resolution automatically.
    
    Args:
        selector_name: Optional selector name override
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get integration instance (this would need to be implemented)
            integration = None  # Would get from global registry
            
            if integration and await integration.is_integration_enabled():
                # Start tracking
                actual_selector_name = selector_name or kwargs.get('selector_name', 'unknown')
                event_id = await integration.on_selector_resolution_start(
                    actual_selector_name,
                    **kwargs
                )
                
                try:
                    # Execute function
                    result = await func(*args, **kwargs)
                    
                    # Complete tracking
                    await integration.on_selector_resolution_complete(
                        event_id,
                        actual_selector_name,
                        success=True,
                        **kwargs
                    )
                    
                    return result
                    
                except Exception as e:
                    # Handle error
                    await integration.on_selector_error(
                        event_id,
                        actual_selector_name,
                        type(e).__name__,
                        str(e),
                        **kwargs
                    )
                    raise
            else:
                # No integration, just execute function
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


@asynccontextmanager
async def selector_telemetry_context(selector_name: str, **context):
    """
    Context manager for selector telemetry tracking.
    
    Args:
        selector_name: Name of selector
        **context: Additional context
    """
    integration = None  # Would get from global registry
    
    if integration and await integration.is_integration_enabled():
        correlation_id = await integration.get_correlation_id(context)
        event_id = await integration.on_selector_resolution_start(
            selector_name,
            correlation_id=correlation_id,
            **context
        )
        
        try:
            yield {
                "correlation_id": correlation_id,
                "event_id": event_id,
                "integration": integration
            }
        except Exception as e:
            await integration.on_selector_error(
                event_id,
                selector_name,
                type(e).__name__,
                str(e),
                correlation_id=correlation_id,
                **context
            )
            raise
    else:
        yield {}
