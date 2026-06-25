"""
Tab Failure Detection and Continuation Logic

Handles tab-specific failure detection, graceful continuation of processing
when tabs fail, and coordination of tab-level recovery actions.
"""

import asyncio
from typing import Dict, Any, Optional, List, Callable, Set
from datetime import datetime
from dataclasses import dataclass, field

from .models.failure_event import FailureEvent, FailureSeverity, FailureCategory, RecoveryAction
from .failure_classifier import classify_failure, is_transient_failure
from .failure_handler import FailureHandler
from .logging.resilience_logger import get_logger
from .correlation import get_correlation_id, with_correlation_id
from .events import publish_failure_event, publish_recovery_event


@dataclass
class TabContext:
    """Context information for a tab being processed."""
    tab_id: str
    job_id: str
    url: str
    status: str = "pending"  # pending, processing, completed, failed, skipped
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    failure_count: int = 0
    last_failure: Optional[FailureEvent] = None
    retry_count: int = 0
    max_retries: int = 3
    context_data: Dict[str, Any] = field(default_factory=dict)
    
    def mark_completed(self) -> None:
        """Mark tab as completed."""
        self.status = "completed"
        self.end_time = datetime.utcnow()
    
    def mark_failed(self, failure: FailureEvent) -> None:
        """Mark tab as failed."""
        self.status = "failed"
        self.end_time = datetime.utcnow()
        self.last_failure = failure
        self.failure_count += 1
    
    def mark_skipped(self) -> None:
        """Mark tab as skipped."""
        self.status = "skipped"
        self.end_time = datetime.utcnow()
    
    def can_retry(self) -> bool:
        """Check if tab can be retried."""
        return self.retry_count < self.max_retries and self.status == "failed"
    
    def increment_retry(self) -> None:
        """Increment retry count."""
        self.retry_count += 1
        self.status = "pending"  # Reset to pending for retry


@dataclass
class TabProcessingResult:
    """Result of tab processing operation."""
    total_tabs: int
    successful_tabs: int
    failed_tabs: int
    skipped_tabs: int
    processing_time: float
    tab_contexts: Dict[str, TabContext]
    failure_events: List[FailureEvent] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_tabs == 0:
            return 0.0
        return (self.successful_tabs / self.total_tabs) * 100
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate percentage."""
        if self.total_tabs == 0:
            return 0.0
        return (self.failed_tabs / self.total_tabs) * 100


class TabHandler:
    """Handles tab processing with graceful failure handling and continuation."""
    
    def __init__(
        self,
        failure_handler: Optional[FailureHandler] = None,
        max_concurrent_tabs: int = 5,
        default_max_retries: int = 3
    ):
        """
        Initialize tab handler.
        
        Args:
            failure_handler: Failure handler instance
            max_concurrent_tabs: Maximum concurrent tab processing
            default_max_retries: Default maximum retries per tab
        """
        self.failure_handler = failure_handler
        self.max_concurrent_tabs = max_concurrent_tabs
        self.default_max_retries = default_max_retries
        self.logger = get_logger("tab_handler")
        self.active_tabs: Dict[str, TabContext] = {}
        self.processing_semaphore = asyncio.Semaphore(max_concurrent_tabs)
    
    async def process_tabs(
        self,
        tab_configs: List[Dict[str, Any]],
        processing_function: Callable,
        job_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> TabProcessingResult:
        """
        Process multiple tabs with graceful failure handling.
        
        Args:
            tab_configs: List of tab configuration dictionaries
            processing_function: Async function to process each tab
            job_id: Job identifier
            context: Additional context
            
        Returns:
            TabProcessingResult with processing statistics
        """
        start_time = datetime.utcnow()
        
        # Create tab contexts
        tab_contexts = {}
        for i, config in enumerate(tab_configs):
            tab_id = config.get("tab_id", f"tab_{i}")
            tab_context = TabContext(
                tab_id=tab_id,
                job_id=job_id,
                url=config.get("url", ""),
                max_retries=config.get("max_retries", self.default_max_retries),
                context_data=config
            )
            tab_contexts[tab_id] = tab_context
            self.active_tabs[tab_id] = tab_context
        
        try:
            # Process tabs concurrently with failure handling
            tasks = []
            for tab_context in tab_contexts.values():
                task = self._process_single_tab(
                    tab_context, processing_function, context or {}
                )
                tasks.append(task)
            
            # Wait for all tasks to complete
            await asyncio.gather(*tasks, return_exceptions=True)
            
        finally:
            # Calculate results
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            successful_tabs = sum(
                1 for ctx in tab_contexts.values() if ctx.status == "completed"
            )
            failed_tabs = sum(
                1 for ctx in tab_contexts.values() if ctx.status == "failed"
            )
            skipped_tabs = sum(
                1 for ctx in tab_contexts.values() if ctx.status == "skipped"
            )
            
            failure_events = [
                ctx.last_failure for ctx in tab_contexts.values()
                if ctx.last_failure is not None
            ]
            
            result = TabProcessingResult(
                total_tabs=len(tab_contexts),
                successful_tabs=successful_tabs,
                failed_tabs=failed_tabs,
                skipped_tabs=skipped_tabs,
                processing_time=processing_time,
                tab_contexts=tab_contexts,
                failure_events=failure_events
            )
            
            # Log processing summary
            self.logger.info(
                f"Tab processing completed: {successful_tabs}/{result.total_tabs} successful "
                f"({result.success_rate:.1f}% success rate)",
                event_type="tab_processing_completed",
                correlation_id=get_correlation_id(),
                context={
                    "job_id": job_id,
                    "total_tabs": result.total_tabs,
                    "successful_tabs": successful_tabs,
                    "failed_tabs": failed_tabs,
                    "skipped_tabs": skipped_tabs,
                    "processing_time": processing_time,
                    "success_rate": result.success_rate
                },
                component="tab_handler"
            )
        
        # Clean up active tabs
        self.active_tabs.clear()
        
        return result
    
    async def _process_single_tab(
        self,
        tab_context: TabContext,
        processing_function: Callable,
        context: Dict[str, Any]
    ) -> None:
        """
        Process a single tab with retry logic and failure handling.
        
        Args:
            tab_context: Tab context information
            processing_function: Function to process the tab
            context: Additional context
        """
        async with self.processing_semaphore:
            with with_correlation_id(get_correlation_id()):
                try:
                    tab_context.status = "processing"
                    
                    self.logger.debug(
                        f"Processing tab: {tab_context.tab_id}",
                        event_type="tab_processing_started",
                        correlation_id=get_correlation_id(),
                        context={
                            "tab_id": tab_context.tab_id,
                            "job_id": tab_context.job_id,
                            "url": tab_context.url
                        },
                        component="tab_handler"
                    )
                    
                    # Process the tab
                    await processing_function(tab_context, context)
                    
                    # Mark as successful
                    tab_context.mark_completed()
                    
                    self.logger.info(
                        f"Tab completed successfully: {tab_context.tab_id}",
                        event_type="tab_completed",
                        correlation_id=get_correlation_id(),
                        context={
                            "tab_id": tab_context.tab_id,
                            "job_id": tab_context.job_id,
                            "processing_time": (
                                datetime.utcnow() - tab_context.start_time
                            ).total_seconds()
                        },
                        component="tab_handler"
                    )
                    
                except Exception as error:
                    # Handle the failure
                    await self._handle_tab_failure(tab_context, error, context)
    
    async def _handle_tab_failure(
        self,
        tab_context: TabContext,
        error: Exception,
        context: Dict[str, Any]
    ) -> None:
        """
        Handle a tab failure with appropriate recovery actions.
        
        Args:
            tab_context: Tab context that failed
            error: The exception that occurred
            context: Additional context
        """
        # Create failure event
        failure_event = FailureEvent(
            severity=FailureSeverity.MEDIUM,
            category=FailureCategory.APPLICATION,
            source="tab_handler",
            message=f"Tab processing failed: {str(error)}",
            context={
                "tab_id": tab_context.tab_id,
                "job_id": tab_context.job_id,
                "url": tab_context.url,
                "retry_count": tab_context.retry_count,
                "failure_count": tab_context.failure_count,
                **context
            }
        )
        
        # Classify the failure
        failure_type, _, _ = classify_failure(error, context)
        
        # Log the failure
        self.logger.error(
            f"Tab failure: {tab_context.tab_id} - {str(error)}",
            event_type="tab_failure",
            correlation_id=get_correlation_id(),
            context={
                "tab_id": tab_context.tab_id,
                "job_id": tab_context.job_id,
                "failure_type": failure_type.value,
                "error": str(error)
            },
            component="tab_handler"
        )
        
        # Handle through failure handler if available
        if self.failure_handler:
            handler_result = await self.failure_handler.handle_failure(
                failure_event.to_dict(), context
            )
            
            if handler_result.get("success", False):
                # Recovery action was successful
                recovery_action = RecoveryAction(
                    handler_result.get("recovery_action", "retry")
                )
                failure_event.mark_resolved(recovery_action)
                
                self.logger.info(
                    f"Tab failure recovered: {tab_context.tab_id}",
                    event_type="tab_failure_recovered",
                    correlation_id=get_correlation_id(),
                    context={
                        "tab_id": tab_context.tab_id,
                        "recovery_action": recovery_action.value
                    },
                    component="tab_handler"
                )
        
        # Determine next action
        if failure_type.value == "transient" and tab_context.can_retry():
            # Retry the tab
            tab_context.increment_retry()
            
            self.logger.info(
                f"Retrying tab: {tab_context.tab_id} (attempt {tab_context.retry_count})",
                event_type="tab_retry",
                correlation_id=get_correlation_id(),
                context={
                    "tab_id": tab_context.tab_id,
                    "retry_count": tab_context.retry_count,
                    "max_retries": tab_context.max_retries
                },
                component="tab_handler"
            )
            
            # Schedule retry (with delay)
            await asyncio.sleep(1.0 * tab_context.retry_count)  # Exponential backoff
            
            # Retry the tab processing
            await self._process_single_tab(tab_context, context.get("processing_function"), context)
            
        else:
            # Mark as failed or skipped
            if failure_type.value == "permanent":
                tab_context.mark_failed(failure_event)
                self.logger.warning(
                    f"Tab permanently failed: {tab_context.tab_id}",
                    event_type="tab_permanently_failed",
                    correlation_id=get_correlation_id(),
                    context={
                        "tab_id": tab_context.tab_id,
                        "failure_reason": str(error)
                    },
                    component="tab_handler"
                )
            else:
                # Max retries exceeded, skip the tab
                tab_context.mark_skipped()
                self.logger.warning(
                    f"Tab skipped after max retries: {tab_context.tab_id}",
                    event_type="tab_skipped",
                    correlation_id=get_correlation_id(),
                    context={
                        "tab_id": tab_context.tab_id,
                        "retry_count": tab_context.retry_count,
                        "max_retries": tab_context.max_retries
                    },
                    component="tab_handler"
                )
    
    def get_active_tab_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all active tabs.
        
        Returns:
            Dictionary mapping tab IDs to status information
        """
        return {
            tab_id: {
                "status": ctx.status,
                "url": ctx.url,
                "failure_count": ctx.failure_count,
                "retry_count": ctx.retry_count,
                "start_time": ctx.start_time.isoformat(),
                "end_time": ctx.end_time.isoformat() if ctx.end_time else None,
                "processing_time": (
                    (ctx.end_time or datetime.utcnow()) - ctx.start_time
                ).total_seconds()
            }
            for tab_id, ctx in self.active_tabs.items()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check and return status."""
        return {
            "status": "healthy",
            "active_tabs": len(self.active_tabs),
            "max_concurrent_tabs": self.max_concurrent_tabs,
            "available_slots": self.max_concurrent_tabs - len(self.active_tabs),
            "active_tab_status": self.get_active_tab_status()
        }


# Global tab handler instance
_tab_handler = TabHandler()


def get_tab_handler() -> TabHandler:
    """Get the global tab handler instance."""
    return _tab_handler


async def process_tabs_with_resilience(
    tab_configs: List[Dict[str, Any]],
    processing_function: Callable,
    job_id: str,
    context: Optional[Dict[str, Any]] = None
) -> TabProcessingResult:
    """Process tabs with resilience using the global tab handler."""
    return await _tab_handler.process_tabs(tab_configs, processing_function, job_id, context)
