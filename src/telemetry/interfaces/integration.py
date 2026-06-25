"""
Selector Telemetry Integration Interface

Abstract interface for integrating telemetry with the Selector Engine
following the contract specification.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime

from ..models import TelemetryEvent


class ISelectorTelemetryIntegration(ABC):
    """
    Interface for integrating telemetry with the Selector Engine.
    
    This interface defines the contract for telemetry integration,
    including event hooks, lifecycle management, and coordination.
    """
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def shutdown_integration(self) -> bool:
        """
        Shutdown telemetry integration.
        
        Returns:
            True if successfully shutdown, False otherwise
            
        Raises:
            TelemetryIntegrationError: If shutdown fails
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def get_correlation_id(self, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate or get correlation ID for operation tracking.
        
        Args:
            context: Optional context for correlation ID generation
            
        Returns:
            Correlation ID
        """
        pass
    
    @abstractmethod
    async def start_operation_session(
        self,
        session_id: str,
        operation_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Start a telemetry session for an operation.
        
        Args:
            session_id: Unique session identifier
            operation_type: Type of operation
            context: Optional session context
            
        Returns:
            True if session started successfully
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def get_active_sessions(self) -> List[Dict[str, Any]]:
        """
        Get list of active telemetry sessions.
        
        Returns:
            List of active session information
        """
        pass
    
    @abstractmethod
    async def is_integration_enabled(self) -> bool:
        """
        Check if telemetry integration is enabled.
        
        Returns:
            True if integration is enabled
        """
        pass
    
    @abstractmethod
    async def enable_integration(self) -> None:
        """
        Enable telemetry integration.
        """
        pass
    
    @abstractmethod
    async def disable_integration(self) -> None:
        """
        Disable telemetry integration.
        """
        pass
    
    @abstractmethod
    async def get_integration_statistics(self) -> Dict[str, Any]:
        """
        Get integration statistics.
        
        Returns:
            Integration statistics including events captured, hooks registered, etc.
        """
        pass
    
    @abstractmethod
    async def get_integration_health(self) -> Dict[str, Any]:
        """
        Get integration health status.
        
        Returns:
            Health status information
        """
        pass
    
    @abstractmethod
    async def configure_integration(self, config: Dict[str, Any]) -> None:
        """
        Configure integration settings.
        
        Args:
            config: Integration configuration
        """
        pass
    
    @abstractmethod
    async def test_integration(self) -> Dict[str, Any]:
        """
        Test integration functionality.
        
        Returns:
            Test results
        """
        pass
    
    @abstractmethod
    async def get_registered_hooks(self) -> List[Dict[str, Any]]:
        """
        Get list of registered hooks.
        
        Returns:
            List of registered hook information
        """
        pass
    
    @abstractmethod
    async def clear_all_hooks(self) -> bool:
        """
        Clear all registered hooks.
        
        Returns:
            True if hooks cleared successfully
        """
        pass
