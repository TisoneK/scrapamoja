"""
Fallback chain execution logic for selector fallback mechanism.

This module implements the core fallback chain execution, primary failure detection,
and fallback selector execution against the same page context.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Optional, List, Dict

from src.models.selector_models import SelectorResult
from src.selectors.context import DOMContext
from src.selectors.engine import SelectorEngine
from src.selectors.exceptions import SelectorError
from src.selectors.fallback.models import (
    FallbackChain,
    FallbackConfig,
    FallbackResult,
    FallbackStatus,
    FailureEvent,
    FailureType,
    FallbackAttempt,
)


class FallbackChainExecutor:
    """
    Executes fallback selector chain when primary selector fails.
    
    This class implements the fallback mechanism as specified in Story 1-2:
    - Detects primary selector failure (empty result or exception)
    - Triggers fallback chain execution
    - Executes fallback selector against same page context
    - Returns fallback result if successful
    - Logs failure events with selector ID, URL, timestamp, and failure type
    """

    def __init__(self, selector_engine: Optional[SelectorEngine] = None):
        """
        Initialize the fallback chain executor.
        
        Args:
            selector_engine: Optional SelectorEngine instance. If not provided,
                           a new one will be created.
        """
        self._selector_engine = selector_engine or SelectorEngine()
        self._logger = self._get_logger()

    def _get_logger(self):
        """Get structured logger for fallback operations."""
        try:
            from src.observability.logger import get_logger
            return get_logger("selector_fallback")
        except ImportError:
            import logging
            return logging.getLogger("selector_fallback")

    def _detect_failure_type(
        self,
        result: SelectorResult,
        error: Optional[Exception] = None
    ) -> FailureType:
        """
        Detect the type of failure from the selector result or error.
        
        Args:
            result: The selector result from primary execution
            error: Optional exception that occurred during execution
            
        Returns:
            FailureType enum value indicating the type of failure
        """
        if error is not None:
            if isinstance(error, asyncio.TimeoutError):
                return FailureType.TIMEOUT
            return FailureType.EXCEPTION
        
        if result is None:
            return FailureType.EXCEPTION
            
        if not result.success:
            return FailureType.EXCEPTION
            
        if result.element_info is None:
            return FailureType.EMPTY_RESULT
            
        if result.confidence_score < 0.5:
            return FailureType.LOW_CONFIDENCE
            
        # Check for empty result content
        if result.element_info.text_content == "":
            return FailureType.EMPTY_RESULT
            
        return FailureType.VALIDATION_FAILED

    def _create_failure_event(
        self,
        selector_name: str,
        context: DOMContext,
        failure_type: FailureType,
        result: Optional[SelectorResult] = None,
        error: Optional[Exception] = None
    ) -> FailureEvent:
        """
        Create a failure event with all relevant details.
        
        Args:
            selector_name: Name of the failed selector
            context: DOM context with URL information
            failure_type: Type of failure detected
            result: Optional selector result
            error: Optional exception
            
        Returns:
            FailureEvent with all captured details
        """
        error_message = None
        if error:
            error_message = str(error)
        elif result and result.failure_reason:
            error_message = result.failure_reason
            
        return FailureEvent(
            selector_id=selector_name,
            url=context.url,
            timestamp=datetime.now(timezone.utc),
            failure_type=failure_type,
            error_message=error_message,
            confidence_score=result.confidence_score if result else None,
            resolution_time=result.resolution_time if result else None,
            context={
                "tab_context": context.tab_context,
                "metadata": context.metadata
            }
        )

    def _log_failure_event(self, failure_event: FailureEvent) -> None:
        """
        Log failure event with structured logging.
        
        Args:
            failure_event: The failure event to log
        """
        self._logger.error(
            "selector_primary_failure",
            extra=failure_event.to_dict()
        )

    def _log_fallback_attempt(self, attempt: FallbackAttempt) -> None:
        """
        Log fallback attempt result.
        
        Args:
            attempt: The fallback attempt to log
        """
        log_level = "info" if attempt.status == FallbackStatus.SUCCESS else "error"
        getattr(self._logger, log_level)(
            "fallback_attempt",
            extra=attempt.to_dict()
        )

    async def execute_with_fallback(
        self,
        selector_name: str,
        context: DOMContext,
        fallback_config: FallbackConfig
    ) -> FallbackResult:
        """
        Execute a selector with fallback support.
        
        This is the main entry point for executing a selector with fallback.
        It first attempts the primary selector, and if it fails, executes
        the fallback selector.
        
        Args:
            selector_name: Name of the primary selector
            context: DOM context for execution
            fallback_config: Configuration for the fallback selector
            
        Returns:
            FallbackResult with primary and fallback execution details
        """
        start_time = time.time()
        
        # Step 1: Try primary selector
        primary_result = None
        primary_error = None
        primary_success = False
        
        try:
            primary_result = await self._selector_engine.resolve(
                selector_name, context
            )
            primary_success = primary_result.success if primary_result else False
        except Exception as e:
            primary_error = e
            primary_success = False
            
        # Step 2: Check if fallback is needed
        if primary_success and primary_result and primary_result.element_info:
            # Primary succeeded - no fallback needed
            chain_duration = time.time() - start_time
            return FallbackResult(
                primary_selector=selector_name,
                primary_success=True,
                fallback_executed=False,
                fallback_success=False,
                final_result=primary_result.element_info,
                chain_duration=chain_duration
            )
        
        # Step 3: Primary failed - detect failure type and log
        failure_type = self._detect_failure_type(primary_result, primary_error)
        failure_event = self._create_failure_event(
            selector_name, context, failure_type, primary_result, primary_error
        )
        self._log_failure_event(failure_event)
        
        # Step 4: Execute fallback if configured
        fallback_executed = False
        fallback_success = False
        fallback_attempt = None
        final_result = None
        
        if fallback_config.enabled:
            fallback_start = time.time()
            fallback_executed = True
            
            try:
                # Execute fallback against same context
                fallback_result = await asyncio.wait_for(
                    self._selector_engine.resolve(
                        fallback_config.selector_name,
                        context
                    ),
                    timeout=fallback_config.timeout_seconds
                )
                
                fallback_resolution_time = time.time() - fallback_start
                
                if fallback_result and fallback_result.success:
                    fallback_success = True
                    final_result = fallback_result.element_info
                    fallback_attempt = FallbackAttempt(
                        fallback_selector=fallback_config.selector_name,
                        status=FallbackStatus.SUCCESS,
                        timestamp=datetime.now(timezone.utc),
                        result=fallback_result.element_info,
                        resolution_time=fallback_resolution_time
                    )
                else:
                    fallback_attempt = FallbackAttempt(
                        fallback_selector=fallback_config.selector_name,
                        status=FallbackStatus.FAILED,
                        timestamp=datetime.now(timezone.utc),
                        error=fallback_result.failure_reason if fallback_result else "Unknown error",
                        resolution_time=fallback_resolution_time
                    )
                    
            except asyncio.TimeoutError:
                fallback_attempt = FallbackAttempt(
                    fallback_selector=fallback_config.selector_name,
                    status=FallbackStatus.FAILED,
                    timestamp=datetime.now(timezone.utc),
                    error=f"Timeout after {fallback_config.timeout_seconds}s",
                    resolution_time=time.time() - fallback_start
                )
            except Exception as e:
                fallback_attempt = FallbackAttempt(
                    fallback_selector=fallback_config.selector_name,
                    status=FallbackStatus.FAILED,
                    timestamp=datetime.now(timezone.utc),
                    error=str(e),
                    resolution_time=time.time() - fallback_start
                )
                
            self._log_fallback_attempt(fallback_attempt)
        
        chain_duration = time.time() - start_time
        
        # Check NFR1: Fallback resolution time should not add more than 5 seconds
        if chain_duration > 5.0:
            self._logger.warning(
                "fallback_chain_exceeded_threshold",
                extra={"chain_duration": chain_duration, "threshold": 5.0}
            )
        
        return FallbackResult(
            primary_selector=selector_name,
            primary_success=primary_success,
            fallback_executed=fallback_executed,
            fallback_success=fallback_success,
            final_result=final_result,
            failure_event=failure_event,
            fallback_attempt=fallback_attempt,
            chain_duration=chain_duration
        )

    async def execute_chain(
        self,
        chain: FallbackChain,
        context: DOMContext
    ) -> FallbackResult:
        """
        Execute a complete fallback chain (primary + all fallbacks).
        
        This method executes the full fallback chain as defined in FallbackChain.
        For Story 1-2, this implements single-level fallback.
        Future stories will add multi-level chaining.
        
        Args:
            chain: The fallback chain configuration
            context: DOM context for execution
            
        Returns:
            FallbackResult with chain execution details
        """
        start_time = time.time()
        
        # Execute primary selector
        primary_result = None
        primary_error = None
        primary_success = False
        
        try:
            primary_result = await self._selector_engine.resolve(
                chain.primary_selector, context
            )
            primary_success = primary_result.success if primary_result else False
        except Exception as e:
            primary_error = e
            primary_success = False
        
        # Check if primary succeeded
        if primary_success and primary_result and primary_result.element_info:
            chain_duration = time.time() - start_time
            return FallbackResult(
                primary_selector=chain.primary_selector,
                primary_success=True,
                fallback_executed=False,
                fallback_success=False,
                final_result=primary_result.element_info,
                chain_duration=chain_duration
            )
        
        # Primary failed - log failure event
        failure_type = self._detect_failure_type(primary_result, primary_error)
        failure_event = self._create_failure_event(
            chain.primary_selector, context, failure_type, primary_result, primary_error
        )
        self._log_failure_event(failure_event)
        
        # Execute fallbacks in priority order
        fallback_executed = False
        fallback_success = False
        fallback_attempt = None
        final_result = None
        
        for fallback_config in chain.fallbacks:
            if not fallback_config.enabled:
                continue
                
            if time.time() - start_time > chain.max_chain_duration:
                self._logger.warning(
                    "fallback_chain_duration_exceeded",
                    extra={"max_duration": chain.max_chain_duration}
                )
                break
            
            fallback_executed = True
            fallback_start = time.time()
            
            try:
                fallback_result = await asyncio.wait_for(
                    self._selector_engine.resolve(
                        fallback_config.selector_name,
                        context
                    ),
                    timeout=fallback_config.timeout_seconds
                )
                
                fallback_resolution_time = time.time() - fallback_start
                
                if fallback_result and fallback_result.success:
                    fallback_success = True
                    final_result = fallback_result.element_info
                    fallback_attempt = FallbackAttempt(
                        fallback_selector=fallback_config.selector_name,
                        status=FallbackStatus.SUCCESS,
                        timestamp=datetime.now(timezone.utc),
                        result=fallback_result.element_info,
                        resolution_time=fallback_resolution_time
                    )
                    break  # Stop at first successful fallback
                else:
                    fallback_attempt = FallbackAttempt(
                        fallback_selector=fallback_config.selector_name,
                        status=FallbackStatus.FAILED,
                        timestamp=datetime.now(timezone.utc),
                        error=fallback_result.failure_reason if fallback_result else "Unknown error",
                        resolution_time=fallback_resolution_time
                    )
                    
            except asyncio.TimeoutError:
                fallback_attempt = FallbackAttempt(
                    fallback_selector=fallback_config.selector_name,
                    status=FallbackStatus.FAILED,
                    timestamp=datetime.now(timezone.utc),
                    error=f"Timeout after {fallback_config.timeout_seconds}s",
                    resolution_time=time.time() - fallback_start
                )
            except Exception as e:
                fallback_attempt = FallbackAttempt(
                    fallback_selector=fallback_config.selector_name,
                    status=FallbackStatus.FAILED,
                    timestamp=datetime.now(timezone.utc),
                    error=str(e),
                    resolution_time=time.time() - fallback_start
                )
        
        if fallback_attempt:
            self._log_fallback_attempt(fallback_attempt)
        
        chain_duration = time.time() - start_time
        
        return FallbackResult(
            primary_selector=chain.primary_selector,
            primary_success=primary_success,
            fallback_executed=fallback_executed,
            fallback_success=fallback_success,
            final_result=final_result,
            failure_event=failure_event,
            fallback_attempt=fallback_attempt,
            chain_duration=chain_duration
        )


def create_fallback_chain(
    primary_selector: str,
    fallback_selectors: List[str]
) -> FallbackChain:
    """
    Helper function to create a fallback chain from selector names.
    
    Args:
        primary_selector: Name of the primary selector
        fallback_selectors: List of fallback selector names in priority order
        
    Returns:
        FallbackChain configured with the given selectors
    """
    fallbacks = [
        FallbackConfig(
            selector_name=name,
            priority=idx + 1,
            enabled=True
        )
        for idx, name in enumerate(fallback_selectors)
    ]
    
    return FallbackChain(
        primary_selector=primary_selector,
        fallbacks=fallbacks
    )
