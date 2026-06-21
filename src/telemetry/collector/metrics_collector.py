"""
Metrics Collector

Main collector for telemetry data from selector operations with
comprehensive metrics gathering and event management.
"""

import asyncio
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..interfaces import ITelemetryCollector
from ..models import (
    TelemetryEvent, PerformanceMetrics, QualityMetrics, 
    StrategyMetrics, ErrorData, ContextData
)
from ..configuration.telemetry_config import TelemetryConfiguration
from ..utils import generate_correlation_id, TimingMeasurement
from ..exceptions import (
    TelemetryCollectionError, TelemetryValidationError,
    StorageUnavailableError, BufferOverflowError
)
from ..configuration.logging import get_logger


class MetricsCollector(ITelemetryCollector):
    """
    Main collector for telemetry data from selector operations.
    
    Collects comprehensive metrics including performance, quality,
    strategy usage, and error data with async processing and buffering.
    """
    
    def __init__(self, config: TelemetryConfiguration, storage_backend=None):
        """
        Initialize metrics collector.
        
        Args:
            config: Telemetry configuration
            storage_backend: Storage backend instance
        """
        self.config = config
        self.storage_backend = storage_backend
        self.logger = get_logger("metrics_collector")
        
        # Event buffer for batch processing
        self._event_buffer: List[TelemetryEvent] = []
        self._buffer_lock = asyncio.Lock()
        
        # Collection state
        self._enabled = config.is_collection_enabled()
        self._collection_stats = {
            "events_collected": 0,
            "events_stored": 0,
            "collection_errors": 0,
            "buffer_overflows": 0,
            "start_time": datetime.utcnow()
        }
        
        # Active sessions for correlation tracking
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        self._sessions_lock = asyncio.Lock()
    
    async def collect_event(
        self,
        selector_name: str,
        operation_type: str,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> TelemetryEvent:
        """
        Collect a telemetry event from a selector operation.
        
        Args:
            selector_name: Name/identifier of the selector
            operation_type: Type of operation (resolution, validation, execution, cleanup)
            correlation_id: Correlation ID for operation tracking
            **kwargs: Additional event data
            
        Returns:
            Collected TelemetryEvent
            
        Raises:
            TelemetryCollectionError: If collection fails
        """
        if not self._enabled:
            raise TelemetryCollectionError(
                "Telemetry collection is disabled",
                error_code="TEL-303"
            )
        
        try:
            # Generate correlation ID if not provided
            if not correlation_id:
                correlation_id = generate_correlation_id()
            
            # Create telemetry event
            event = TelemetryEvent(
                event_id=str(uuid.uuid4()),
                correlation_id=correlation_id,
                selector_name=selector_name,
                timestamp=datetime.utcnow(),
                operation_type=operation_type,
                performance_metrics=kwargs.get("performance_metrics"),
                quality_metrics=kwargs.get("quality_metrics"),
                strategy_metrics=kwargs.get("strategy_metrics"),
                error_data=kwargs.get("error_data"),
                context_data=kwargs.get("context_data")
            )
            
            # Validate event
            await self._validate_event(event)
            
            # Add to buffer
            await self._add_to_buffer(event)
            
            # Update statistics
            self._collection_stats["events_collected"] += 1
            
            self.logger.event_collected(
                event.event_id,
                selector_name,
                operation_type=operation_type,
                correlation_id=correlation_id
            )
            
            return event
            
        except Exception as e:
            self._collection_stats["collection_errors"] += 1
            self.logger.error(
                "Failed to collect telemetry event",
                selector_name=selector_name,
                operation_type=operation_type,
                error=str(e)
            )
            raise TelemetryCollectionError(
                f"Failed to collect event: {e}",
                error_code="TEL-304",
                correlation_id=correlation_id
            )
    
    async def record_event(self, event: TelemetryEvent) -> bool:
        """
        Record a telemetry event for storage.
        
        Args:
            event: TelemetryEvent to record
            
        Returns:
            True if successfully recorded, False otherwise
            
        Raises:
            TelemetryCollectionError: If recording fails
        """
        try:
            # Validate event
            await self._validate_event(event)
            
            # Add to buffer
            await self._add_to_buffer(event)
            
            # Update statistics
            self._collection_stats["events_collected"] += 1
            
            self.logger.event_collected(
                event.event_id,
                event.selector_name,
                operation_type=event.operation_type,
                correlation_id=event.correlation_id
            )
            
            return True
            
        except Exception as e:
            self._collection_stats["collection_errors"] += 1
            self.logger.error(
                "Failed to record telemetry event",
                event_id=event.event_id,
                error=str(e)
            )
            raise TelemetryCollectionError(
                f"Failed to record event: {e}",
                error_code="TEL-305",
                correlation_id=event.correlation_id
            )
    
    async def collect_performance_metrics(
        self,
        selector_name: str,
        resolution_time_ms: float,
        strategy_execution_time_ms: float,
        total_duration_ms: float,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Collect performance metrics for a selector operation.
        
        Args:
            selector_name: Name/identifier of the selector
            resolution_time_ms: Time taken for selector resolution
            strategy_execution_time_ms: Time for strategy execution
            total_duration_ms: Total operation duration
            correlation_id: Correlation ID for operation tracking
            **kwargs: Additional performance data
            
        Returns:
            Performance metrics dictionary
            
        Raises:
            TelemetryCollectionError: If collection fails
        """
        try:
            # Create performance metrics
            performance_metrics = PerformanceMetrics(
                resolution_time_ms=resolution_time_ms,
                strategy_execution_time_ms=strategy_execution_time_ms,
                total_duration_ms=total_duration_ms,
                memory_usage_mb=kwargs.get("memory_usage_mb"),
                cpu_usage_percent=kwargs.get("cpu_usage_percent"),
                network_requests_count=kwargs.get("network_requests_count"),
                dom_operations_count=kwargs.get("dom_operations_count")
            )
            
            # Convert to dictionary
            metrics_dict = performance_metrics.to_dict()
            
            # Update session if correlation ID provided
            if correlation_id:
                await self._update_session_metrics(correlation_id, "performance", metrics_dict)
            
            return metrics_dict
            
        except Exception as e:
            self.logger.error(
                "Failed to collect performance metrics",
                selector_name=selector_name,
                error=str(e)
            )
            raise TelemetryCollectionError(
                f"Failed to collect performance metrics: {e}",
                error_code="TEL-306",
                correlation_id=correlation_id
            )
    
    async def collect_quality_metrics(
        self,
        selector_name: str,
        confidence_score: float,
        success: bool,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Collect quality metrics for a selector operation.
        
        Args:
            selector_name: Name/identifier of the selector
            confidence_score: Confidence score (0.0-1.0)
            success: Whether the operation succeeded
            correlation_id: Correlation ID for operation tracking
            **kwargs: Additional quality data
            
        Returns:
            Quality metrics dictionary
            
        Raises:
            TelemetryCollectionError: If collection fails
        """
        try:
            # Create quality metrics
            quality_metrics = QualityMetrics(
                confidence_score=confidence_score,
                success=success,
                elements_found=kwargs.get("elements_found"),
                strategy_success_rate=kwargs.get("strategy_success_rate"),
                drift_detected=kwargs.get("drift_detected"),
                fallback_used=kwargs.get("fallback_used"),
                validation_passed=kwargs.get("validation_passed")
            )
            
            # Convert to dictionary
            metrics_dict = quality_metrics.to_dict()
            
            # Update session if correlation ID provided
            if correlation_id:
                await self._update_session_metrics(correlation_id, "quality", metrics_dict)
            
            return metrics_dict
            
        except Exception as e:
            self.logger.error(
                "Failed to collect quality metrics",
                selector_name=selector_name,
                error=str(e)
            )
            raise TelemetryCollectionError(
                f"Failed to collect quality metrics: {e}",
                error_code="TEL-307",
                correlation_id=correlation_id
            )
    
    async def collect_strategy_metrics(
        self,
        selector_name: str,
        primary_strategy: str,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Collect strategy metrics for a selector operation.
        
        Args:
            selector_name: Name/identifier of the selector
            primary_strategy: Primary strategy used
            correlation_id: Correlation ID for operation tracking
            **kwargs: Additional strategy data
            
        Returns:
            Strategy metrics dictionary
            
        Raises:
            TelemetryCollectionError: If collection fails
        """
        try:
            # Create strategy metrics
            strategy_metrics = StrategyMetrics(
                primary_strategy=primary_strategy,
                secondary_strategies=kwargs.get("secondary_strategies", []),
                strategy_execution_order=kwargs.get("strategy_execution_order", []),
                strategy_success_by_type=kwargs.get("strategy_success_by_type", {}),
                strategy_timing_by_type=kwargs.get("strategy_timing_by_type", {}),
                strategy_switches_count=kwargs.get("strategy_switches_count", 0)
            )
            
            # Convert to dictionary
            metrics_dict = strategy_metrics.to_dict()
            
            # Update session if correlation ID provided
            if correlation_id:
                await self._update_session_metrics(correlation_id, "strategy", metrics_dict)
            
            return metrics_dict
            
        except Exception as e:
            self.logger.error(
                "Failed to collect strategy metrics",
                selector_name=selector_name,
                error=str(e)
            )
            raise TelemetryCollectionError(
                f"Failed to collect strategy metrics: {e}",
                error_code="TEL-308",
                correlation_id=correlation_id
            )
    
    async def collect_error_data(
        self,
        selector_name: str,
        error_type: str,
        error_message: str,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Collect error data for a failed selector operation.
        
        Args:
            selector_name: Name/identifier of the selector
            error_type: Type of error
            error_message: Error message
            correlation_id: Correlation ID for operation tracking
            **kwargs: Additional error data
            
        Returns:
            Error data dictionary
            
        Raises:
            TelemetryCollectionError: If collection fails
        """
        try:
            # Create error data
            error_data = ErrorData(
                error_type=error_type,
                error_message=error_message,
                stack_trace=kwargs.get("stack_trace"),
                retry_attempts=kwargs.get("retry_attempts", 0),
                fallback_attempts=kwargs.get("fallback_attempts", 0),
                recovery_successful=kwargs.get("recovery_successful")
            )
            
            # Convert to dictionary
            error_dict = error_data.to_dict()
            
            # Update session if correlation ID provided
            if correlation_id:
                await self._update_session_metrics(correlation_id, "error", error_dict)
            
            return error_dict
            
        except Exception as e:
            self.logger.error(
                "Failed to collect error data",
                selector_name=selector_name,
                error_type=error_type,
                error=str(e)
            )
            raise TelemetryCollectionError(
                f"Failed to collect error data: {e}",
                error_code="TEL-309",
                correlation_id=correlation_id
            )
    
    async def collect_context_data(
        self,
        selector_name: str,
        browser_session_id: str,
        tab_context_id: str,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Collect context data for a selector operation.
        
        Args:
            selector_name: Name/identifier of the selector
            browser_session_id: Browser session identifier
            tab_context_id: Tab context identifier
            correlation_id: Correlation ID for operation tracking
            **kwargs: Additional context data
            
        Returns:
            Context data dictionary
            
        Raises:
            TelemetryCollectionError: If collection fails
        """
        try:
            # Create context data
            context_data = ContextData(
                browser_session_id=browser_session_id,
                tab_context_id=tab_context_id,
                page_url=kwargs.get("page_url"),
                page_title=kwargs.get("page_title"),
                user_agent=kwargs.get("user_agent"),
                viewport_size=kwargs.get("viewport_size"),
                timestamp_context=kwargs.get("timestamp_context")
            )
            
            # Convert to dictionary
            context_dict = context_data.to_dict()
            
            # Update session if correlation ID provided
            if correlation_id:
                await self._update_session_metrics(correlation_id, "context", context_dict)
            
            return context_dict
            
        except Exception as e:
            self.logger.error(
                "Failed to collect context data",
                selector_name=selector_name,
                error=str(e)
            )
            raise TelemetryCollectionError(
                f"Failed to collect context data: {e}",
                error_code="TEL-310",
                correlation_id=correlation_id
            )
    
    async def get_buffer_status(self) -> Dict[str, Any]:
        """
        Get current buffer status.
        
        Returns:
            Buffer status information including size, usage, and health
        """
        async with self._buffer_lock:
            buffer_size = len(self._event_buffer)
            max_size = self.config.get_buffer_size()
            usage_percent = (buffer_size / max_size) * 100 if max_size > 0 else 0
            
            return {
                "current_size": buffer_size,
                "max_size": max_size,
                "usage_percent": usage_percent,
                "is_full": buffer_size >= max_size,
                "health_status": "healthy" if usage_percent < 80 else "warning" if usage_percent < 95 else "critical"
            }
    
    async def flush_buffer(self) -> int:
        """
        Flush the event buffer to storage.
        
        Returns:
            Number of events flushed
            
        Raises:
            TelemetryCollectionError: If flush fails
        """
        if not self.storage_backend:
            raise TelemetryCollectionError(
                "No storage backend configured",
                error_code="TEL-311"
            )
        
        try:
            async with self._buffer_lock:
                if not self._event_buffer:
                    return 0
                
                # Get events to flush
                events_to_flush = self._event_buffer.copy()
                self._event_buffer.clear()
            
            # Store events
            stored_count = 0
            for event in events_to_flush:
                try:
                    success = await self.storage_backend.store_event(event)
                    if success:
                        stored_count += 1
                        self._collection_stats["events_stored"] += 1
                        
                        self.logger.event_stored(
                            event.event_id,
                            type(self.storage_backend).__name__
                        )
                except Exception as e:
                    self.logger.storage_error(
                        "store_event",
                        str(e),
                        event_id=event.event_id
                    )
            
            return stored_count
            
        except Exception as e:
            self.logger.error(
                "Failed to flush buffer",
                error=str(e)
            )
            raise TelemetryCollectionError(
                f"Failed to flush buffer: {e}",
                error_code="TEL-312"
            )
    
    async def is_enabled(self) -> bool:
        """
        Check if telemetry collection is enabled.
        
        Returns:
            True if collection is enabled
        """
        return self._enabled
    
    async def enable_collection(self) -> None:
        """
        Enable telemetry collection.
        """
        self._enabled = True
        self.logger.info("Telemetry collection enabled")
    
    async def disable_collection(self) -> None:
        """
        Disable telemetry collection.
        """
        self._enabled = False
        self.logger.info("Telemetry collection disabled")
    
    async def get_collection_statistics(self) -> Dict[str, Any]:
        """
        Get collection statistics.
        
        Returns:
            Collection statistics including events collected, errors, etc.
        """
        runtime = datetime.utcnow() - self._collection_stats["start_time"]
        
        return {
            **self._collection_stats,
            "runtime_seconds": runtime.total_seconds(),
            "events_per_second": (
                self._collection_stats["events_collected"] / runtime.total_seconds()
                if runtime.total_seconds() > 0 else 0
            ),
            "error_rate": (
                self._collection_stats["collection_errors"] / 
                max(1, self._collection_stats["events_collected"])
            ),
            "storage_success_rate": (
                self._collection_stats["events_stored"] / 
                max(1, self._collection_stats["events_collected"])
            ),
            "enabled": self._enabled
        }
    
    async def validate_event(self, event: TelemetryEvent) -> List[str]:
        """
        Validate a telemetry event.
        
        Args:
            event: TelemetryEvent to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        return await self._validate_event(event)
    
    async def start_collection_session(self, session_id: str) -> None:
        """
        Start a collection session.
        
        Args:
            session_id: Unique session identifier
        """
        async with self._sessions_lock:
            self._active_sessions[session_id] = {
                "session_id": session_id,
                "start_time": datetime.utcnow(),
                "events": [],
                "metrics": {}
            }
        
        self.logger.info("Collection session started", session_id=session_id)
    
    async def end_collection_session(self, session_id: str) -> Dict[str, Any]:
        """
        End a collection session and get session statistics.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session statistics
        """
        async with self._sessions_lock:
            if session_id not in self._active_sessions:
                raise TelemetryCollectionError(
                    f"Session {session_id} not found",
                    error_code="TEL-313"
                )
            
            session = self._active_sessions.pop(session_id)
            session["end_time"] = datetime.utcnow()
            session["duration_ms"] = (
                session["end_time"] - session["start_time"]
            ).total_seconds() * 1000
            session["event_count"] = len(session["events"])
        
        self.logger.info(
            "Collection session ended",
            session_id=session_id,
            duration_ms=session["duration_ms"],
            event_count=session["event_count"]
        )
        
        return session
    
    # Private methods
    
    async def _validate_event(self, event: TelemetryEvent) -> List[str]:
        """Validate a telemetry event."""
        from ..utils.validation import validate_telemetry_data
        
        errors = validate_telemetry_data(event, "event")
        
        if errors:
            raise TelemetryValidationError(
                f"Event validation failed: {'; '.join(errors)}",
                validation_errors=errors,
                correlation_id=event.correlation_id
            )
        
        return errors
    
    async def _add_to_buffer(self, event: TelemetryEvent) -> None:
        """Add event to buffer with overflow protection."""
        async with self._buffer_lock:
            buffer_size = len(self._event_buffer)
            max_size = self.config.get_buffer_size()
            
            if buffer_size >= max_size:
                # Buffer overflow - trigger graceful degradation
                self._collection_stats["buffer_overflows"] += 1
                self.logger.buffer_overflow(
                    max_size,
                    buffer_size
                )
                
                # Remove oldest events to make room
                overflow_count = buffer_size - max_size + 1
                self._event_buffer = self._event_buffer[overflow_count:]
                
                raise BufferOverflowError(
                    max_size,
                    buffer_size,
                    correlation_id=event.correlation_id
                )
            
            self._event_buffer.append(event)
    
    async def _update_session_metrics(
        self,
        correlation_id: str,
        metric_type: str,
        metrics: Dict[str, Any]
    ) -> None:
        """Update session metrics."""
        async with self._sessions_lock:
            # Find session by correlation ID
            for session in self._active_sessions.values():
                if correlation_id in session.get("events", []):
                    if "metrics" not in session:
                        session["metrics"] = {}
                    session["metrics"][metric_type] = metrics
                    break
