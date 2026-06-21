"""
Telemetry Hooks for Selector Engine

Hook implementations for integrating telemetry collection with
the Selector Engine without modifying core selector logic.
"""

import asyncio
import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from functools import wraps

from ..utils import generate_correlation_id, TimingMeasurement
from ..exceptions import TelemetryIntegrationError
from ..configuration.logging import get_logger


class TelemetryHooks:
    """
    Collection of telemetry hooks for selector engine integration.
    
    Provides ready-to-use hooks for common selector operations
    with automatic correlation ID management and performance tracking.
    """
    
    def __init__(self, integration=None):
        """
        Initialize telemetry hooks.
        
        Args:
            integration: Selector telemetry integration instance
        """
        self.integration = integration
        self.logger = get_logger("telemetry_hooks")
        
        # Hook statistics
        self._hook_stats = {
            "hooks_executed": 0,
            "hooks_failed": 0,
            "start_time": datetime.utcnow()
        }
    
    async def before_resolution_hook(self, context: Dict[str, Any]) -> None:
        """
        Hook called before selector resolution starts.
        
        Args:
            context: Hook context containing selector information
        """
        try:
            selector_name = context.get("selector_name", "unknown")
            correlation_id = context.get("correlation_id")
            
            # Generate correlation ID if not provided
            if not correlation_id and self.integration:
                correlation_id = await self.integration.get_correlation_id({
                    "selector_name": selector_name,
                    "operation": "resolution"
                })
                context["correlation_id"] = correlation_id
            
            # Store correlation ID in thread local if available
            if correlation_id:
                from ..utils import set_thread_correlation_id
                set_thread_correlation_id(correlation_id)
            
            self._hook_stats["hooks_executed"] += 1
            
            self.logger.debug(
                "Before resolution hook executed",
                selector_name=selector_name,
                correlation_id=correlation_id
            )
            
        except Exception as e:
            self._hook_stats["hooks_failed"] += 1
            self.logger.error(
                "Before resolution hook failed",
                error=str(e)
            )
    
    async def after_resolution_hook(self, context: Dict[str, Any]) -> None:
        """
        Hook called after selector resolution completes.
        
        Args:
            context: Hook context containing resolution results
        """
        try:
            selector_name = context.get("selector_name", "unknown")
            correlation_id = context.get("correlation_id")
            success = context.get("success", False)
            confidence_score = context.get("confidence_score")
            elements_found = context.get("elements_found")
            
            # Clear thread local correlation ID
            from ..utils import clear_thread_correlation_id
            clear_thread_correlation_id()
            
            self._hook_stats["hooks_executed"] += 1
            
            self.logger.debug(
                "After resolution hook executed",
                selector_name=selector_name,
                correlation_id=correlation_id,
                success=success
            )
            
        except Exception as e:
            self._hook_stats["hooks_failed"] += 1
            self.logger.error(
                "After resolution hook failed",
                error=str(e)
            )
    
    async def before_strategy_hook(self, context: Dict[str, Any]) -> None:
        """
        Hook called before strategy execution starts.
        
        Args:
            context: Hook context containing strategy information
        """
        try:
            selector_name = context.get("selector_name", "unknown")
            strategy_name = context.get("strategy_name", "unknown")
            correlation_id = context.get("correlation_id")
            
            self._hook_stats["hooks_executed"] += 1
            
            self.logger.debug(
                "Before strategy hook executed",
                selector_name=selector_name,
                strategy_name=strategy_name,
                correlation_id=correlation_id
            )
            
        except Exception as e:
            self._hook_stats["hooks_failed"] += 1
            self.logger.error(
                "Before strategy hook failed",
                error=str(e)
            )
    
    async def after_strategy_hook(self, context: Dict[str, Any]) -> None:
        """
        Hook called after strategy execution completes.
        
        Args:
            context: Hook context containing strategy results
        """
        try:
            selector_name = context.get("selector_name", "unknown")
            strategy_name = context.get("strategy_name", "unknown")
            correlation_id = context.get("correlation_id")
            success = context.get("success", False)
            execution_time_ms = context.get("execution_time_ms", 0)
            
            self._hook_stats["hooks_executed"] += 1
            
            self.logger.debug(
                "After strategy hook executed",
                selector_name=selector_name,
                strategy_name=strategy_name,
                correlation_id=correlation_id,
                success=success
            )
            
        except Exception as e:
            self._hook_stats["hooks_failed"] += 1
            self.logger.error(
                "After strategy hook failed",
                error=str(e)
            )
    
    async def on_error_hook(self, context: Dict[str, Any]) -> None:
        """
        Hook called when an error occurs during selector operations.
        
        Args:
            context: Hook context containing error information
        """
        try:
            selector_name = context.get("selector_name", "unknown")
            error_type = context.get("error_type", "unknown")
            error_message = context.get("error_message", "")
            correlation_id = context.get("correlation_id")
            
            # Clear thread local correlation ID on error
            from ..utils import clear_thread_correlation_id
            clear_thread_correlation_id()
            
            self._hook_stats["hooks_executed"] += 1
            
            self.logger.warning(
                "Error hook executed",
                selector_name=selector_name,
                error_type=error_type,
                correlation_id=correlation_id
            )
            
        except Exception as e:
            self._hook_stats["hooks_failed"] += 1
            self.logger.error(
                "Error hook failed",
                error=str(e)
            )
    
    async def on_performance_hook(self, context: Dict[str, Any]) -> None:
        """
        Hook called when performance metrics are updated.
        
        Args:
            context: Hook context containing performance information
        """
        try:
            selector_name = context.get("selector_name", "unknown")
            metric_name = context.get("metric_name", "unknown")
            metric_value = context.get("metric_value", 0)
            correlation_id = context.get("correlation_id")
            
            self._hook_stats["hooks_executed"] += 1
            
            self.logger.debug(
                "Performance hook executed",
                selector_name=selector_name,
                metric_name=metric_name,
                metric_value=metric_value,
                correlation_id=correlation_id
            )
            
        except Exception as e:
            self._hook_stats["hooks_failed"] += 1
            self.logger.error(
                "Performance hook failed",
                error=str(e)
            )
    
    def get_hook_statistics(self) -> Dict[str, Any]:
        """
        Get hook execution statistics.
        
        Returns:
            Hook statistics
        """
        runtime = datetime.utcnow() - self._hook_stats["start_time"]
        
        return {
            **self._hook_stats,
            "runtime_seconds": runtime.total_seconds(),
            "hooks_per_second": (
                self._hook_stats["hooks_executed"] / runtime.total_seconds()
                if runtime.total_seconds() > 0 else 0
            ),
            "error_rate": (
                self._hook_stats["hooks_failed"] / max(1, self._hook_stats["hooks_executed"])
            )
        }


# Decorator-based hooks for easy integration

def track_selector_call(selector_name_param: str = "selector_name"):
    """
    Decorator to automatically track selector calls.
    
    Args:
        selector_name_param: Parameter name that contains selector name
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get integration instance
            integration = None  # Would get from global registry
            
            if integration and await integration.is_integration_enabled():
                # Extract selector name
                selector_name = kwargs.get(selector_name_param, "unknown")
                
                # Start tracking
                event_id = await integration.on_selector_resolution_start(
                    selector_name,
                    **kwargs
                )
                
                try:
                    # Execute function
                    result = await func(*args, **kwargs)
                    
                    # Complete tracking with success
                    await integration.on_selector_resolution_complete(
                        event_id,
                        selector_name,
                        success=True,
                        **kwargs
                    )
                    
                    return result
                    
                except Exception as e:
                    # Handle error
                    await integration.on_selector_error(
                        event_id,
                        selector_name,
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


def track_strategy_call(strategy_name_param: str = "strategy_name"):
    """
    Decorator to automatically track strategy calls.
    
    Args:
        strategy_name_param: Parameter name that contains strategy name
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get integration instance
            integration = None  # Would get from global registry
            
            if integration and await integration.is_integration_enabled():
                # Extract strategy and selector names
                strategy_name = kwargs.get(strategy_name_param, "unknown")
                selector_name = kwargs.get("selector_name", "unknown")
                event_id = kwargs.get("event_id", f"strategy_{int(time.time() * 1000)}")
                
                # Start strategy tracking
                await integration.on_strategy_execution_start(
                    event_id,
                    strategy_name,
                    selector_name,
                    **kwargs
                )
                
                start_time = time.time()
                
                try:
                    # Execute function
                    result = await func(*args, **kwargs)
                    
                    # Complete strategy tracking
                    execution_time_ms = (time.time() - start_time) * 1000
                    await integration.on_strategy_execution_complete(
                        event_id,
                        strategy_name,
                        success=True,
                        execution_time_ms=execution_time_ms,
                        selector_name=selector_name,
                        **kwargs
                    )
                    
                    return result
                    
                except Exception as e:
                    # Handle error
                    execution_time_ms = (time.time() - start_time) * 1000
                    await integration.on_strategy_execution_complete(
                        event_id,
                        strategy_name,
                        success=False,
                        execution_time_ms=execution_time_ms,
                        selector_name=selector_name,
                        **kwargs
                    )
                    raise
            else:
                # No integration, just execute function
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def track_performance_metrics(metric_name: str):
    """
    Decorator to track performance metrics.
    
    Args:
        metric_name: Name of the metric being tracked
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get integration instance
            integration = None  # Would get from global registry
            
            if integration and await integration.is_integration_enabled():
                selector_name = kwargs.get("selector_name", "unknown")
                correlation_id = kwargs.get("correlation_id")
                event_id = kwargs.get("event_id", f"perf_{int(time.time() * 1000)}")
                
                start_time = time.time()
                
                try:
                    # Execute function
                    result = await func(*args, **kwargs)
                    
                    # Track performance
                    execution_time_ms = (time.time() - start_time) * 1000
                    await integration.on_selector_performance_update(
                        event_id,
                        selector_name,
                        metric_name,
                        execution_time_ms,
                        correlation_id=correlation_id,
                        **kwargs
                    )
                    
                    return result
                    
                except Exception as e:
                    # Still track performance even on error
                    execution_time_ms = (time.time() - start_time) * 1000
                    await integration.on_selector_performance_update(
                        event_id,
                        selector_name,
                        metric_name,
                        execution_time_ms,
                        correlation_id=correlation_id,
                        error=str(e),
                        **kwargs
                    )
                    raise
            else:
                # No integration, just execute function
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# Context manager for automatic tracking

class SelectorTelemetryContext:
    """
    Context manager for automatic selector telemetry tracking.
    
    Provides automatic correlation ID management and performance
    tracking for selector operations.
    """
    
    def __init__(self, selector_name: str, integration=None, **context):
        """
        Initialize telemetry context.
        
        Args:
            selector_name: Name of selector
            integration: Telemetry integration instance
            **context: Additional context
        """
        self.selector_name = selector_name
        self.integration = integration
        self.context = context
        self.logger = get_logger("telemetry_context")
        
        # Tracking state
        self.event_id = None
        self.correlation_id = None
        self.start_time = None
        self.active = False
    
    async def __aenter__(self):
        """Enter context and start tracking."""
        if self.integration and await self.integration.is_integration_enabled():
            try:
                # Generate correlation ID
                self.correlation_id = await self.integration.get_correlation_id({
                    "selector_name": self.selector_name,
                    **self.context
                })
                
                # Start tracking
                self.event_id = await self.integration.on_selector_resolution_start(
                    self.selector_name,
                    self.correlation_id,
                    **self.context
                )
                
                self.start_time = time.time()
                self.active = True
                
                # Set thread local correlation ID
                from ..utils import set_thread_correlation_id
                set_thread_correlation_id(self.correlation_id)
                
                self.logger.debug(
                    "Telemetry context entered",
                    selector_name=self.selector_name,
                    correlation_id=self.correlation_id,
                    event_id=self.event_id
                )
                
            except Exception as e:
                self.logger.error(
                    "Failed to enter telemetry context",
                    selector_name=self.selector_name,
                    error=str(e)
                )
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context and complete tracking."""
        if self.active and self.integration:
            try:
                execution_time_ms = (time.time() - self.start_time) * 1000 if self.start_time else 0
                
                if exc_type is None:
                    # Success case
                    await self.integration.on_selector_resolution_complete(
                        self.event_id,
                        self.selector_name,
                        success=True,
                        execution_time_ms=execution_time_ms,
                        correlation_id=self.correlation_id,
                        **self.context
                    )
                else:
                    # Error case
                    await self.integration.on_selector_error(
                        self.event_id,
                        self.selector_name,
                        exc_type.__name__ if exc_type else "UnknownError",
                        str(exc_val) if exc_val else "Unknown error",
                        correlation_id=self.correlation_id,
                        execution_time_ms=execution_time_ms,
                        **self.context
                    )
                
                # Clear thread local correlation ID
                from ..utils import clear_thread_correlation_id
                clear_thread_correlation_id()
                
                self.active = False
                
                self.logger.debug(
                    "Telemetry context exited",
                    selector_name=self.selector_name,
                    correlation_id=self.correlation_id,
                    success=exc_type is None
                )
                
            except Exception as e:
                self.logger.error(
                    "Failed to exit telemetry context",
                    selector_name=self.selector_name,
                    error=str(e)
                )
    
    def update_context(self, **kwargs):
        """Update context information."""
        self.context.update(kwargs)
    
    def get_correlation_id(self) -> Optional[str]:
        """Get correlation ID for this context."""
        return self.correlation_id
    
    def get_event_id(self) -> Optional[str]:
        """Get event ID for this context."""
        return self.event_id


# Utility functions for easy integration

async def create_selector_context(selector_name: str, integration=None, **context):
    """
    Create a selector telemetry context.
    
    Args:
        selector_name: Name of selector
        integration: Telemetry integration instance
        **context: Additional context
        
    Returns:
        SelectorTelemetryContext instance
    """
    return SelectorTelemetryContext(selector_name, integration, **context)


def with_telemetry_tracking(selector_name_param: str = "selector_name"):
    """
    Decorator to add telemetry tracking to any function.
    
    Args:
        selector_name_param: Parameter name containing selector name
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            selector_name = kwargs.get(selector_name_param, "unknown")
            
            async with create_selector_context(selector_name, **kwargs) as ctx:
                # Update context with function-specific information
                ctx.update_context(
                    function_name=func.__name__,
                    args=args,
                    kwargs=kwargs
                )
                
                # Execute function
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# Hook registration utilities

async def register_default_hooks(integration, hooks_instance=None):
    """
    Register default telemetry hooks with integration.
    
    Args:
        integration: Selector telemetry integration instance
        hooks_instance: Optional hooks instance
    """
    if hooks_instance is None:
        hooks_instance = TelemetryHooks(integration)
    
    # Register hooks
    await integration.register_selector_hook(
        "*",  # All selectors
        "before_resolution",
        hooks_instance.before_resolution_hook
    )
    
    await integration.register_selector_hook(
        "*",
        "after_resolution", 
        hooks_instance.after_resolution_hook
    )
    
    await integration.register_selector_hook(
        "*",
        "before_strategy",
        hooks_instance.before_strategy_hook
    )
    
    await integration.register_selector_hook(
        "*",
        "after_strategy",
        hooks_instance.after_strategy_hook
    )
    
    await integration.register_selector_hook(
        "*",
        "on_error",
        hooks_instance.on_error_hook
    )
    
    await integration.register_selector_hook(
        "*",
        "on_performance",
        hooks_instance.on_performance_hook
    )
    
    return hooks_instance


# Global hook registry for easy access

_global_hooks: Optional[TelemetryHooks] = None


def get_global_hooks() -> Optional[TelemetryHooks]:
    """Get global hooks instance."""
    return _global_hooks


def set_global_hooks(hooks: TelemetryHooks) -> None:
    """Set global hooks instance."""
    global _global_hooks
    _global_hooks = hooks


async def initialize_global_hooks(integration) -> TelemetryHooks:
    """Initialize global hooks instance."""
    global _global_hooks
    _global_hooks = TelemetryHooks(integration)
    await register_default_hooks(integration, _global_hooks)
    return _global_hooks
