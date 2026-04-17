"""
Fallback chain execution logic for selector fallback mechanism.

This module implements the core fallback chain execution, primary failure detection,
and fallback selector execution against the same page context.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Type

from src.models.selector_models import SelectorResult
from src.selectors.context import DOMContext
from src.selectors.engine import SelectorEngine
from src.selectors.exceptions import SelectorError
from src.selectors.fallback.models import (
    FailureEvent,
    FailureType,
    FallbackAttempt,
    FallbackChain,
    FallbackConfig,
    FallbackResult,
    FallbackStatus,
)
from src.selectors.hints.strategy import HintBasedFallbackStrategy


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
        self._validator = None  # Lazy load to avoid circular import

    def _get_logger(self):
        """Get structured logger for fallback operations."""
        try:
            from src.observability.logger import get_logger

            return get_logger("selector_fallback")
        except ImportError:
            import logging

            return logging.getLogger("selector_fallback")

    def _detect_failure_type(
        self, result: SelectorResult, error: Optional[Exception] = None
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
        error: Optional[Exception] = None,
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
            context={"tab_context": context.tab_context, "metadata": context.metadata},
        )

    def _log_failure_event(self, failure_event: FailureEvent) -> None:
        """
        Log failure event with structured logging.

        Args:
            failure_event: The failure event to log
        """
        self._logger.error("selector_primary_failure", extra=failure_event.to_dict())

    def _log_fallback_attempt(self, attempt: FallbackAttempt) -> None:
        """
        Log fallback attempt result.

        Args:
            attempt: The fallback attempt to log
        """
        log_level = "info" if attempt.status == FallbackStatus.SUCCESS else "error"
        getattr(self._logger, log_level)("fallback_attempt", extra=attempt.to_dict())

    async def execute_with_fallback(
        self, selector_name: str, context: DOMContext, fallback_config: FallbackConfig
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
        attempted_selectors: List[Dict[str, Any]] = []

        try:
            primary_result = await self._selector_engine.resolve(selector_name, context)
            primary_success = primary_result.success if primary_result else False
            # Track primary selector attempt
            attempted_selectors.append({
                "name": selector_name,
                "result": "success" if primary_success else "failure",
                "reason": primary_result.failure_reason if primary_result and not primary_success else None,
                "value": str(primary_result.element_info) if primary_result and primary_result.element_info else None,
                "resolution_time_ms": primary_result.resolution_time if primary_result else 0.0,
            })
        except Exception as e:
            primary_error = e
            primary_success = False
            # Track primary selector failure
            attempted_selectors.append({
                "name": selector_name,
                "result": "failure",
                "reason": str(e),
                "value": None,
                "resolution_time_ms": 0.0,
            })

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
                chain_duration=chain_duration,
            )

        # Step 3: Primary failed - detect failure type and log
        failure_type = self._detect_failure_type(primary_result, primary_error)
        failure_event = self._create_failure_event(
            selector_name, context, failure_type, primary_result, primary_error
        )
        # Use validation hook for additional failure detection (Story 3-1)
        if self._validator is None:
            from src.selectors.hooks.post_extraction import PostExtractionValidator
            self._validator = PostExtractionValidator()
        validator_failure = self._validator.validate_result(
            result=primary_result.element_info if primary_result else None,
            selector_id=selector_name,
            page_url=context.url,
            extractor_id=context.tab_context or "unknown",
            exception=primary_error,
        )
        # Use validator failure event if ours didn't create one
        if validator_failure and failure_event is None:
            failure_event = validator_failure
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
                        fallback_config.selector_name, context
                    ),
                    timeout=fallback_config.timeout_seconds,
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
                        resolution_time=fallback_resolution_time,
                    )
                else:
                    fallback_attempt = FallbackAttempt(
                        fallback_selector=fallback_config.selector_name,
                        status=FallbackStatus.FAILED,
                        timestamp=datetime.now(timezone.utc),
                        error=fallback_result.failure_reason
                        if fallback_result
                        else "Unknown error",
                        resolution_time=fallback_resolution_time,
                    )

            except asyncio.TimeoutError:
                fallback_attempt = FallbackAttempt(
                    fallback_selector=fallback_config.selector_name,
                    status=FallbackStatus.FAILED,
                    timestamp=datetime.now(timezone.utc),
                    error=f"Timeout after {fallback_config.timeout_seconds}s",
                    resolution_time=time.time() - fallback_start,
                )
            except Exception as e:
                fallback_attempt = FallbackAttempt(
                    fallback_selector=fallback_config.selector_name,
                    status=FallbackStatus.FAILED,
                    timestamp=datetime.now(timezone.utc),
                    error=str(e),
                    resolution_time=time.time() - fallback_start,
                )

            # Track fallback selector attempt (Story 3-2: Full Context Logging)
            attempted_selectors.append({
                "name": fallback_config.selector_name,
                "result": "success" if fallback_success else "failure",
                "reason": fallback_attempt.error if fallback_attempt else None,
                "value": str(final_result) if final_result else None,
                "resolution_time_ms": fallback_attempt.resolution_time * 1000 if fallback_attempt else 0.0,
            })

            self._log_fallback_attempt(fallback_attempt)

        chain_duration = time.time() - start_time

        # Check NFR1: Fallback resolution time should not add more than 5 seconds
        if chain_duration > 5.0:
            self._logger.warning(
                "fallback_chain_exceeded_threshold",
                extra={"chain_duration": chain_duration, "threshold": 5.0},
            )

        return FallbackResult(
            primary_selector=selector_name,
            primary_success=primary_success,
            fallback_executed=fallback_executed,
            fallback_success=fallback_success,
            final_result=final_result,
            failure_event=failure_event,
            fallback_attempt=fallback_attempt,
            chain_duration=chain_duration,
            attempted_selectors=attempted_selectors,  # Story 3-2: Track all attempted selectors
        )

    async def execute_chain(
        self, chain: FallbackChain, context: DOMContext
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
                chain_duration=chain_duration,
            )

        # Primary failed - log failure event
        failure_type = self._detect_failure_type(primary_result, primary_error)
        failure_event = self._create_failure_event(
            chain.primary_selector, context, failure_type, primary_result, primary_error
        )
        # Use validation hook for additional failure detection (Story 3-1)
        if self._validator is None:
            from src.selectors.hooks.post_extraction import PostExtractionValidator
            self._validator = PostExtractionValidator()
        validator_failure = self._validator.validate_result(
            result=primary_result.element_info if primary_result else None,
            selector_id=chain.primary_selector,
            page_url=context.url,
            extractor_id=context.tab_context or "unknown",
            exception=primary_error,
        )
        # Use validator failure event if ours didn't create one
        if validator_failure and failure_event is None:
            failure_event = validator_failure
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
                    extra={"max_duration": chain.max_chain_duration},
                )
                break

            fallback_executed = True
            fallback_start = time.time()

            try:
                fallback_result = await asyncio.wait_for(
                    self._selector_engine.resolve(
                        fallback_config.selector_name, context
                    ),
                    timeout=fallback_config.timeout_seconds,
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
                        resolution_time=fallback_resolution_time,
                    )
                    break  # Stop at first successful fallback
                else:
                    fallback_attempt = FallbackAttempt(
                        fallback_selector=fallback_config.selector_name,
                        status=FallbackStatus.FAILED,
                        timestamp=datetime.now(timezone.utc),
                        error=fallback_result.failure_reason
                        if fallback_result
                        else "Unknown error",
                        resolution_time=fallback_resolution_time,
                    )

            except asyncio.TimeoutError:
                fallback_attempt = FallbackAttempt(
                    fallback_selector=fallback_config.selector_name,
                    status=FallbackStatus.FAILED,
                    timestamp=datetime.now(timezone.utc),
                    error=f"Timeout after {fallback_config.timeout_seconds}s",
                    resolution_time=time.time() - fallback_start,
                )
            except Exception as e:
                fallback_attempt = FallbackAttempt(
                    fallback_selector=fallback_config.selector_name,
                    status=FallbackStatus.FAILED,
                    timestamp=datetime.now(timezone.utc),
                    error=str(e),
                    resolution_time=time.time() - fallback_start,
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
            chain_duration=chain_duration,
        )

    async def execute_with_hint_strategy(
        self,
        primary_selector: str,
        hint,
        context: DOMContext,
        max_chain_duration: float = 5.0,
    ) -> FallbackResult:
        """
        Execute a fallback chain built from a SelectorHint.

        This thin orchestrator delegates chain construction to
        HintBasedFallbackStrategy and chain execution to the existing
        execute_chain() method (which remains unchanged).

        Args:
            primary_selector: Name of the primary selector
            hint: SelectorHint containing strategy and alternatives
            context: DOM context for execution
            max_chain_duration: Maximum allowed chain duration in seconds

        Returns:
            FallbackResult with chain execution details
        """
        from src.selectors.hints.strategy import HintBasedFallbackStrategy

        strategy = HintBasedFallbackStrategy()
        chain = strategy.build_chain_from_hint(
            primary_selector, hint, max_chain_duration
        )
        
        # Compute stability scores for the result (AC3.1, AC3.2)
        stability_scores, stability_source = self._compute_stability_scores(
            strategy, hint, chain.fallbacks
        )

        self._logger.debug(
            "hint_strategy_chain_executing",
            extra={
                "primary": primary_selector,
                "strategy": hint.strategy,
                "fallback_count": len(chain.fallbacks),
                "stability_scores": stability_scores,
                "stability_source": stability_source,
            },
        )
        
        result = await self.execute_chain(chain, context)
        
        # Populate stability metadata in result (Task 3.1, 3.2)
        result.stability_scores = stability_scores
        result.stability_source = stability_source
        
        return result

    def _compute_stability_scores(
        self,
        strategy: HintBasedFallbackStrategy,
        hint,
        fallbacks: List[FallbackConfig],
    ) -> tuple[Dict[str, float], str]:
        """
        Compute stability scores from hint for FallbackResult.
        
        Args:
            strategy: HintBasedFallbackStrategy instance
            hint: SelectorHint with stability information
            fallbacks: List of FallbackConfig from the chain
            
        Returns:
            Tuple of (stability_scores dict, stability_source string)
        """
        stability_scores: Dict[str, float] = {}
        stability_source = "yaml"
        
        # Get default stability from hint
        default_stability = hint.stability if hint.stability is not None else 0.5
        
        # Get per-alternative stability from metadata if available
        stability_map = hint.metadata.get("stability_scores", {}) if hint.metadata else {}
        
        # For adaptive strategy, we'll mark the source appropriately
        if hint.strategy == "adaptive":
            stability_source = "adaptive"
        else:
            stability_source = "yaml"
        
        # Build stability scores for each fallback
        for fb in fallbacks:
            # Use per-alternative score if available, otherwise use default
            stability_scores[fb.selector_name] = stability_map.get(
                fb.selector_name, default_stability
            )
        
        return stability_scores, stability_source


def create_fallback_chain(
    primary_selector: str, fallback_selectors: List[str]
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
        FallbackConfig(selector_name=name, priority=idx + 1, enabled=True)
        for idx, name in enumerate(fallback_selectors)
    ]

    return FallbackChain(primary_selector=primary_selector, fallbacks=fallbacks)


# Story 4-1: Adaptive API Integration


class AdaptiveAPIIntegration:
    """
    Integration helper for calling the adaptive API to get selector alternatives.

    This class provides methods to:
    - Call the adaptive API for alternatives when YAML fallbacks fail
    - Extend the fallback chain with API-returned alternatives
    - Handle graceful degradation when API is unavailable
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0,
        enabled: bool = True,
    ) -> None:
        """
        Initialize the adaptive API integration.

        Args:
            base_url: Base URL of the adaptive API
            timeout: Request timeout in seconds
            enabled: Whether API integration is enabled
        """
        self.base_url = base_url
        self.timeout = timeout
        self.enabled = enabled
        self._client = None
        self._logger = self._get_logger()

    def _get_logger(self) -> Any:
        """Get structured logger for adaptive API operations."""
        try:
            from src.observability.logger import get_logger

            return get_logger("adaptive_api_integration")
        except ImportError:
            import logging

            return logging.getLogger("adaptive_api_integration")

    async def get_alternatives(
        self,
        selector_id: str,
        page_url: str,
    ) -> List[str]:
        """
        Get alternative selectors from the adaptive API.

        Args:
            selector_id: The ID of the selector that failed
            page_url: The URL of the page where the selector failed

        Returns:
            List of alternative selector strings (empty list if none available)
        """
        if not self.enabled:
            self._logger.debug("adaptive_api_disabled")
            return []

        try:
            from src.selectors.adaptive import AdaptiveAPIClient

            client = await AdaptiveAPIClient.get_instance(
                base_url=self.base_url,
                timeout=self.timeout,
            )

            response = await client.get_alternatives(selector_id, page_url)

            if response.success and response.alternatives:
                alternatives = [alt.selector for alt in response.alternatives]
                self._logger.info(
                    "adaptive_api_alternatives_found",
                    extra={
                        "selector_id": selector_id,
                        "alternatives_count": len(alternatives),
                    },
                )
                return alternatives

            if response.error:
                self._logger.warning(
                    "adaptive_api_error",
                    extra={"selector_id": selector_id, "error": response.error},
                )

            return []

        except Exception as e:
            self._logger.error(
                "adaptive_api_exception",
                extra={"selector_id": selector_id, "error": str(e)},
            )
            return []

    async def execute_with_api_alternatives(
        self,
        executor: "FallbackChainExecutor",
        primary_selector: str,
        context: DOMContext,
        chain: FallbackChain,
    ) -> FallbackResult:
        """
        Execute fallback chain with adaptive API alternatives.

        This method:
        1. First executes the existing YAML-defined fallback chain
        2. If all fallbacks fail, calls the adaptive API for alternatives
        3. Tries those alternatives as additional fallbacks

        Args:
            executor: FallbackChainExecutor instance
            primary_selector: Name of the primary selector
            context: DOM context for execution
            chain: Existing FallbackChain with YAML-defined fallbacks

        Returns:
            FallbackResult with API alternatives if available
        """
        # Step 1: Execute existing fallback chain first
        result = await executor.execute_chain(chain, context)

        # Step 2: If fallback succeeded, return early
        if result.fallback_success:
            result.stability_source = "yaml"
            return result

        # Step 3: All YAML fallbacks failed - try adaptive API
        self._logger.info(
            "yaml_fallbacks_exhausted_trying_api",
            extra={"primary_selector": primary_selector},
        )

        alternatives = await self.get_alternatives(primary_selector, context.url)

        if not alternatives:
            self._logger.info(
                "no_api_alternatives_available",
                extra={"primary_selector": primary_selector},
            )
            result.stability_source = "yaml"
            return result

        # Step 4: Try API alternatives
        self._logger.info(
            "trying_api_alternatives",
            extra={
                "primary_selector": primary_selector,
                "alternatives_count": len(alternatives),
            },
        )

        # Track that we're now using API alternatives
        result.api_alternatives = alternatives
        result.stability_source = "adaptive"

        # Try each alternative
        for idx, alternative_selector in enumerate(alternatives):
            # Check time budget
            if result.chain_duration > 5.0:  # NFR1: Max 5 seconds
                self._logger.warning("chain_duration_exceeded_api_alternatives")
                break

            alt_start = time.time()
            alt_priority = len(chain.fallbacks) + idx + 1

            try:
                alt_result = await asyncio.wait_for(
                    executor._selector_engine.resolve(alternative_selector, context),
                    timeout=30.0,
                )

                alt_resolution_time = time.time() - alt_start

                if alt_result and alt_result.success:
                    # Success! Use this alternative
                    result.fallback_executed = True
                    result.fallback_success = True
                    result.final_result = alt_result.element_info
                    result.chain_duration = time.time() - (result.chain_duration - result.chain_duration)

                    # Record the attempt
                    result.attempted_selectors.append({
                        "name": alternative_selector,
                        "result": "success",
                        "source": "adaptive_api",
                        "resolution_time_ms": alt_resolution_time * 1000,
                    })

                    result.fallback_attempt = FallbackAttempt(
                        fallback_selector=alternative_selector,
                        status=FallbackStatus.SUCCESS,
                        timestamp=datetime.now(timezone.utc),
                        result=alt_result.element_info,
                        resolution_time=alt_resolution_time,
                    )

                    self._logger.info(
                        "api_alternative_succeeded",
                        extra={"selector": alternative_selector},
                    )
                    break

                # Record failed attempt
                result.attempted_selectors.append({
                    "name": alternative_selector,
                    "result": "failure",
                    "source": "adaptive_api",
                    "reason": alt_result.failure_reason if alt_result else "unknown",
                    "resolution_time_ms": alt_resolution_time * 1000,
                })

            except asyncio.TimeoutError:
                result.attempted_selectors.append({
                    "name": alternative_selector,
                    "result": "failure",
                    "source": "adaptive_api",
                    "reason": "timeout",
                    "resolution_time_ms": (time.time() - alt_start) * 1000,
                })
            except Exception as e:
                result.attempted_selectors.append({
                    "name": alternative_selector,
                    "result": "failure",
                    "source": "adaptive_api",
                    "reason": str(e),
                    "resolution_time_ms": (time.time() - alt_start) * 1000,
                })

        return result

    async def close(self) -> None:
        """Close the adaptive API client."""
        if self._client is not None:
            # Client is managed by AdaptiveAPIClient singleton
            # Just reset our reference
            self._client = None
