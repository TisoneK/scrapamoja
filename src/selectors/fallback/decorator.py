"""
Fallback decorator for declarative fallback chain definition.

This module provides the @with_fallback decorator that allows declarative
fallback chain definition for selector extraction functions.

Usage:
    @with_fallback(fallbacks=["fallback_selector_1", "fallback_selector_2"])
    async def extract_primary(page, context):
        ...
"""

import asyncio
import functools
import time
from datetime import datetime, timezone
from typing import Any, Callable, List, Optional, Union

from src.selectors.context import DOMContext
from src.selectors.engine import SelectorEngine
from src.selectors.exceptions import FallbackError, SelectorError
from src.selectors.fallback.chain import FallbackChainExecutor
from src.selectors.fallback.models import (
    FallbackChain,
    FallbackConfig,
    FallbackResult,
    FallbackStatus,
)
from src.selectors.fallback.logging import get_fallback_logger
from src.models.selector_models import SelectorResult, ElementInfo


def _get_logger():
    """Get structured logger for fallback decorator operations."""
    try:
        from src.observability.logger import get_logger
        return get_logger("selector_fallback_decorator")
    except ImportError:
        import logging
        return logging.getLogger("selector_fallback_decorator")


class FallbackDecorator:
    """
    Decorator class for managing fallback chains on extraction functions.
    
    This class wraps extraction functions with fallback chain support,
    allowing declarative specification of fallback selectors.
    """
    
    def __init__(
        self,
        fallback_selectors: List[str],
        primary_selector: Optional[str] = None,
        max_chain_duration: float = 5.0,
        timeout_seconds: float = 30.0,
        selector_engine: Optional[SelectorEngine] = None,
    ):
        """
        Initialize the fallback decorator.
        
        Args:
            fallback_selectors: List of fallback selector names in priority order
            primary_selector: Name of the primary selector (derived from function name if not provided)
            max_chain_duration: Maximum time allowed for the entire chain (seconds)
            timeout_seconds: Timeout for each selector execution
            selector_engine: Optional SelectorEngine instance
        """
        if len(fallback_selectors) < 2:
            raise ValueError("At least two fallback selectors are required for multi-level fallback chain (AC1 requirement)")
            
        self.fallback_selectors = fallback_selectors
        self.primary_selector = primary_selector
        self.max_chain_duration = max_chain_duration
        self.timeout_seconds = timeout_seconds
        self._selector_engine = selector_engine
        self._executor: Optional[FallbackChainExecutor] = None
        self._logger = _get_logger()
        self._fallback_logger = get_fallback_logger()
    
    @property
    def executor(self) -> FallbackChainExecutor:
        """Lazy initialization of FallbackChainExecutor."""
        if self._executor is None:
            self._executor = FallbackChainExecutor(self._selector_engine)
        return self._executor
    
    def _create_fallback_chain(self, primary_selector: str) -> FallbackChain:
        """Create a FallbackChain from the decorator configuration."""
        fallbacks = [
            FallbackConfig(
                selector_name=name,
                priority=idx + 1,
                enabled=True,
                timeout_seconds=self.timeout_seconds,
            )
            for idx, name in enumerate(self.fallback_selectors)
        ]
        
        return FallbackChain(
            primary_selector=primary_selector,
            fallbacks=fallbacks,
            max_chain_duration=self.max_chain_duration,
        )
    
    async def execute(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> FallbackResult:
        """
        Execute the decorated function with fallback chain support.
        
        Args:
            func: The decorated extraction function
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            FallbackResult with chain execution details
        """
        # Extract context from args/kwargs
        context: Optional[DOMContext] = None
        for arg in args:
            if isinstance(arg, DOMContext):
                context = arg
                break
        if not context:
            context = kwargs.get('context')
            
        if not context:
            raise FallbackError(
                message="DOMContext is required for fallback chain execution",
                attempted_selectors=[self.primary_selector] + self.fallback_selectors if self.primary_selector else self.fallback_selectors
            )
        
        # Get page URL for logging
        page_url = context.url if hasattr(context, 'url') else "unknown"
        
        # Determine primary selector name
        primary_selector = self.primary_selector
        if not primary_selector:
            # Try to derive from function name
            func_name = func.__name__
            if func_name.startswith('extract_'):
                primary_selector = func_name[8:]  # Remove 'extract_' prefix
            elif func_name.startswith('get_'):
                primary_selector = func_name[4:]  # Remove 'get_' prefix
            else:
                primary_selector = func_name
        
        # Create fallback chain
        chain = self._create_fallback_chain(primary_selector)
        
        start_time = time.time()
        
        # Step 1: Try primary selector using SelectorEngine (as per story requirements)
        primary_result = None
        primary_success = False
        primary_error = None
        
        try:
            # Use SelectorEngine.resolve for primary selector execution
            # This ensures proper integration with the selector system
            primary_engine_result = await self.executor._selector_engine.resolve(
                primary_selector, context
            )
            if primary_engine_result and primary_engine_result.success:
                primary_success = True
                primary_result = primary_engine_result.element_info
            else:
                primary_success = False
                if primary_engine_result:
                    primary_error = Exception(primary_engine_result.failure_reason or "Primary selector failed")
        except Exception as e:
            primary_error = e
            primary_success = False
            self._logger.warning(
                "primary_extraction_failed",
                extra={
                    "selector": primary_selector,
                    "error": str(e),
                    "function": func.__name__
                }
            )
        
        chain_duration = time.time() - start_time
        
        # Step 2: If primary succeeded, return success
        if primary_success and primary_result is not None:
            # Convert to ElementInfo if needed
            final_result = primary_result
            if isinstance(primary_result, SelectorResult):
                final_result = primary_result.element_info
            elif isinstance(primary_result, dict):
                final_result = primary_result.get('element_info')
            
            result = FallbackResult(
                primary_selector=primary_selector,
                primary_success=True,
                fallback_executed=False,
                fallback_success=False,
                final_result=final_result,
                chain_duration=chain_duration
            )
            
            # Log the primary-only success (AC1 - primary success)
            try:
                self._fallback_logger.log_primary_only_success(
                    selector_id=primary_selector,
                    page_url=page_url,
                    result=final_result,
                    resolution_time_ms=chain_duration * 1000
                )
            except Exception as logging_error:
                # Never let logging failures affect the main flow
                self._logger.warning(
                    "fallback_logging_failed",
                    extra={"error": str(logging_error)}
                )
            
            return result
        
        # Step 3: Primary failed - execute fallback chain
        self._logger.info(
            "primary_failed_executing_fallbacks",
            extra={"primary_selector": primary_selector}
        )
        
        fallback_result = await self.executor.execute_chain(chain, context)
        
        # Update chain duration to include primary attempt
        total_duration = time.time() - start_time
        fallback_result.chain_duration = total_duration
        
        # Check NFR1: Fallback Resolution Time
        if total_duration > self.max_chain_duration:
            self._logger.warning(
                "fallback_chain_exceeded_threshold",
                extra={
                    "chain_duration": total_duration,
                    "threshold": self.max_chain_duration
                }
            )
        
        # Log the complete fallback attempt (AC1, AC2, AC3)
        try:
            self._fallback_logger.log_fallback_attempt(
                fallback_result=fallback_result,
                page_url=page_url,
                selector_id=primary_selector
            )
        except Exception as logging_error:
            # Never let logging failures affect the main flow
            self._logger.warning(
                "fallback_logging_failed",
                extra={"error": str(logging_error)}
            )
        
        return fallback_result


def with_fallback(
    fallbacks: List[str],
    primary_selector: Optional[str] = None,
    max_chain_duration: float = 5.0,
    timeout_seconds: float = 30.0,
) -> Callable:
    """
    Decorator to add fallback chain support to an extraction function.
    
    This decorator allows declarative specification of fallback selectors,
    enabling multi-level fallback execution with automatic performance tracking.
    
    Args:
        fallbacks: List of fallback selector names in priority order (fallback1, fallback2, ...)
        primary_selector: Optional name of the primary selector (derived from function name if not provided)
        max_chain_duration: Maximum time allowed for the entire chain (seconds). Default: 5.0 (NFR1)
        timeout_seconds: Timeout for each selector execution. Default: 30.0
        
    Returns:
        A decorated function that executes with fallback chain support
        
    Example:
        @with_fallback(fallbacks=["fallback_title_v2", "fallback_title_alt"])
        async def extract_title(page, context: DOMContext):
            result = await selector_engine.resolve("title_v1", context)
            return result.element_info
            
        # Or with explicit primary selector:
        @with_fallback(
            fallbacks=["fallback_price", "alt_price"],
            primary_selector="price_main"
        )
        async def extract_price(page, context: DOMContext):
            ...
    
    Note:
        - The decorated function must accept a DOMContext as argument
        - The function should return SelectorResult, ElementInfo, or a value that can be interpreted as success/failure
        - Fallback execution stops at the first successful selector
    """
    def decorator(func: Callable) -> Callable:
        # Create decorator configuration
        decorator_config = FallbackDecorator(
            fallback_selectors=fallbacks,
            primary_selector=primary_selector,
            max_chain_duration=max_chain_duration,
            timeout_seconds=timeout_seconds,
        )
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute with fallback chain
            return await decorator_config.execute(func, *args, **kwargs)
        
        # Attach metadata for introspection
        wrapper._fallback_config = decorator_config
        wrapper._is_fallback_enabled = True
        
        return wrapper
    
    return decorator


def create_fallback_decorator(
    fallback_selectors: List[str],
    **options
) -> Callable:
    """
    Factory function to create a fallback decorator with custom options.
    
    This is useful when you want to reuse the same fallback configuration
    across multiple functions.
    
    Args:
        fallback_selectors: List of fallback selector names
        **options: Additional options (max_chain_duration, timeout_seconds, etc.)
        
    Returns:
        A configured fallback decorator
        
    Example:
        # Create a reusable decorator
        price_fallback = create_fallback_decorator(
            ["fallback_price_v2", "fallback_price_alt"],
            max_chain_duration=3.0
        )
        
        @price_fallback
        async def extract_price(page, context):
            ...
    """
    def decorator_factory(fallbacks: List[str]) -> Callable:
        return with_fallback(fallbacks=fallbacks, **options)
    
    return decorator_factory
