"""
Hint-based fallback strategy for selector fallback chain construction.

This module provides HintBasedFallbackStrategy, which converts a SelectorHint
into a FallbackChain by applying the strategy declared in the hint
(linear, priority, adaptive, or stability) and any custom rules stored in hint metadata.
"""

from typing import Any, Dict, List, Optional

from src.selectors.exceptions import SelectorConfigurationError, AdaptiveModuleUnavailableError
from src.selectors.fallback.models import FallbackChain, FallbackConfig
from src.selectors.hints.models import SelectorHint


class HintBasedFallbackStrategy:
    """Builds a FallbackChain from a SelectorHint using the hint's declared strategy.

    Supported strategies:
        - ``linear``   : alternatives tried in listed order (default)
        - ``priority`` : alternatives ordered by per-alternative priority values
                         stored in ``hint.metadata["priorities"]``
        - ``stability``: alternatives ordered by stability score from hints (highest first)
        - ``adaptive`` : uses historical stability data from adaptive module, merges
                         with YAML hints (weighted: 30% YAML, 70% historical)

    Custom rules (``hint.metadata["rules"]``) are applied as a post-processing
    pass on top of whichever strategy was selected:
        - ``{"type": "skip",   "selector": "<name>"}`` – removes the alternative
        - ``{"type": "prefer", "selector": "<name>"}`` – moves the alternative to
          the front of the chain (highest priority)
        - Unrecognized rule types are silently skipped (logged at DEBUG).
    """

    def __init__(self) -> None:
        self._logger = self._get_logger()

    # ------------------------------------------------------------------
    # Logger helper (mirrors pattern used across the codebase)
    # ------------------------------------------------------------------

    def _get_logger(self):
        """Get structured logger for hint strategy operations."""
        try:
            from src.observability.logger import get_logger

            return get_logger("selector_hints_strategy")
        except ImportError:
            import logging

            return logging.getLogger("selector_hints_strategy")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_chain_from_hint(
        self,
        primary_selector: str,
        hint: SelectorHint,
        max_duration: float = 5.0,
    ) -> FallbackChain:
        """Build a FallbackChain from a SelectorHint.

        Args:
            primary_selector: Name of the primary selector.
            hint: SelectorHint describing the fallback alternatives and strategy.
            max_duration: Maximum allowed chain duration in seconds (NFR1).

        Returns:
            A FallbackChain ready for execution by FallbackChainExecutor.

        Raises:
            SelectorConfigurationError: If ``hint.alternatives`` is empty.
        """
        if not hint.alternatives:
            raise SelectorConfigurationError(
                message=(
                    "Hint has no alternatives defined; "
                    "cannot build a fallback chain for selector"
                ),
                selector_id=primary_selector,
            )

        alternatives = list(hint.alternatives)

        # Apply declared strategy to obtain the ordered FallbackConfig list
        if hint.strategy == "linear":
            fallbacks = self._apply_linear_strategy(alternatives)
        elif hint.strategy == "priority":
            fallbacks = self._apply_priority_strategy(alternatives, hint.metadata)
        elif hint.strategy == "stability":
            fallbacks = self._apply_stability_strategy(alternatives, hint)
        elif hint.strategy == "adaptive":
            fallbacks = self._apply_adaptive_strategy_sync(alternatives, hint)
        else:
            # Defensive branch: SelectorHint.__post_init__ already rejects unknown
            # strategies, but guard here in case of future changes.
            self._logger.warning(
                "unknown_strategy_falling_back_to_linear",
                extra={"strategy": hint.strategy, "primary": primary_selector},
            )
            fallbacks = self._apply_linear_strategy(alternatives)

        # Apply custom rules as a post-processing pass when rules are present
        if hint.metadata and "rules" in hint.metadata:
            fallbacks = self._apply_custom_rules(fallbacks, hint.metadata)

        self._logger.debug(
            "hint_strategy_applied",
            extra={
                "strategy": hint.strategy,
                "primary": primary_selector,
                "fallback_count": len(fallbacks),
            },
        )

        return FallbackChain(
            primary_selector=primary_selector,
            fallbacks=fallbacks,
            max_chain_duration=max_duration,
        )

    # ------------------------------------------------------------------
    # Strategy implementations
    # ------------------------------------------------------------------

    def _apply_linear_strategy(self, alternatives: List[str]) -> List[FallbackConfig]:
        """Order alternatives exactly as listed (default behaviour).

        Args:
            alternatives: Ordered list of alternative selector names.

        Returns:
            FallbackConfig list with priorities 1, 2, 3, … matching list order.
        """
        return [
            FallbackConfig(selector_name=name, priority=i + 1)
            for i, name in enumerate(alternatives)
        ]

    def _apply_priority_strategy(
        self,
        alternatives: List[str],
        metadata: Optional[Dict[str, Any]],
    ) -> List[FallbackConfig]:
        """Order alternatives by per-alternative priority values from metadata.

        Priority values live at ``metadata["priorities"]``, a mapping of
        ``{selector_name: int}``.  Higher values are attempted first.
        Selectors absent from the map receive a default mid-priority of 5.

        Args:
            alternatives: List of alternative selector names.
            metadata: Hint metadata dict (may be None).

        Returns:
            FallbackConfig list sorted by descending priority value.
        """
        priorities_map: Dict[str, int] = (
            metadata.get("priorities", {}) if metadata else {}
        )

        def _priority_score(name: str) -> int:
            return priorities_map.get(name, 5)

        sorted_names = sorted(alternatives, key=_priority_score, reverse=True)
        return [
            FallbackConfig(selector_name=name, priority=i + 1)
            for i, name in enumerate(sorted_names)
        ]

    async def _apply_adaptive_strategy(
        self,
        alternatives: List[str],
        hint: SelectorHint,
    ) -> List[FallbackConfig]:
        """Apply adaptive strategy using historical stability data from adaptive module.

        Queries the adaptive module for historical stability metrics and merges
        with YAML hint stability using weighted average (30% YAML, 70% historical).
        Falls back to stability strategy if adaptive module is unavailable.

        Args:
            alternatives: List of alternative selector names.
            hint: The originating SelectorHint with stability and metadata.

        Returns:
            FallbackConfig list sorted by combined stability score (highest first).
        """
        # Step 1: Get YAML stability from hint (default 0.5)
        yaml_stability = hint.stability if hint.stability is not None else 0.5

        # Step 2: Query adaptive module for historical data
        historical_data = None
        try:
            historical_data = await self._query_adaptive_module(alternatives)
        except AdaptiveModuleUnavailableError as e:
            self._logger.warning(
                "adaptive_module_unavailable_using_yaml_stability",
                extra={"reason": str(e)}
            )
            # Fall back to stability strategy using YAML hints only
            return self._apply_stability_strategy(alternatives, hint)

        # Step 3: Merge YAML + historical (weighted: 30% YAML, 70% historical)
        merged_scores = {}
        for alt in alternatives:
            historical = historical_data.get(alt, {}).get("avg_stability", yaml_stability)
            merged_scores[alt] = 0.3 * yaml_stability + 0.7 * historical

        # Sort by merged stability score (highest first)
        sorted_alts = sorted(alternatives, key=lambda a: merged_scores.get(a, 0.5), reverse=True)

        self._logger.debug(
            "adaptive_strategy_applied",
            extra={
                "alternatives": alternatives,
                "merged_scores": merged_scores,
                "sorted_order": sorted_alts
            }
        )

        return [
            FallbackConfig(selector_name=name, priority=i + 1)
            for i, name in enumerate(sorted_alts)
        ]

    def _apply_adaptive_strategy_sync(
        self,
        alternatives: List[str],
        hint: SelectorHint,
    ) -> List[FallbackConfig]:
        """Synchronous version of _apply_adaptive_strategy for non-async contexts.

        Falls back to stability strategy if adaptive module is unavailable.

        Args:
            alternatives: List of alternative selector names.
            hint: The originating SelectorHint with stability and metadata.

        Returns:
            FallbackConfig list sorted by combined stability score (highest first).
        """
        # Step 1: Get YAML stability from hint (default 0.5)
        yaml_stability = hint.stability if hint.stability is not None else 0.5

        # Step 2: Try synchronous query
        historical_data = None
        try:
            historical_data = self._query_adaptive_module_sync(alternatives)
        except AdaptiveModuleUnavailableError as e:
            self._logger.warning(
                "adaptive_module_unavailable_using_yaml_stability",
                extra={"reason": str(e)}
            )
            return self._apply_stability_strategy(alternatives, hint)

        # Step 3: Merge YAML + historical (weighted: 30% YAML, 70% historical)
        merged_scores = {}
        for alt in alternatives:
            historical = historical_data.get(alt, {}).get("avg_stability", yaml_stability)
            merged_scores[alt] = 0.3 * yaml_stability + 0.7 * historical

        sorted_alts = sorted(alternatives, key=lambda a: merged_scores.get(a, 0.5), reverse=True)

        self._logger.debug(
            "adaptive_strategy_applied",
            extra={
                "alternatives": alternatives,
                "merged_scores": merged_scores,
                "sorted_order": sorted_alts
            }
        )

        return [
            FallbackConfig(selector_name=name, priority=i + 1)
            for i, name in enumerate(sorted_alts)
        ]

    def _apply_stability_strategy(
        self,
        alternatives: List[str],
        hint: SelectorHint,
    ) -> List[FallbackConfig]:
        """Order alternatives by stability score from YAML hints (highest first).

        Uses the hint.stability field to determine the stability score for
        each alternative. If an alternative doesn't have a specific stability
        value in metadata, uses the default hint stability.

        Args:
            alternatives: List of alternative selector names.
            hint: The originating SelectorHint with stability and metadata.

        Returns:
            FallbackConfig list sorted by stability score (highest first).
        """
        # Get default stability from hint (default 0.5)
        default_stability = hint.stability if hint.stability is not None else 0.5

        # Get per-alternative stability from metadata if available
        stability_map = hint.metadata.get("stability_scores", {}) if hint.metadata else {}

        # Build stability scores for each alternative
        stability_scores = {}
        for alt in alternatives:
            stability_scores[alt] = stability_map.get(alt, default_stability)

        # Sort by stability score (highest first)
        sorted_alts = sorted(alternatives, key=lambda a: stability_scores.get(a, 0.5), reverse=True)

        self._logger.debug(
            "stability_strategy_applied",
            extra={
                "alternatives": alternatives,
                "stability_scores": stability_scores,
                "sorted_order": sorted_alts
            }
        )

        return [
            FallbackConfig(selector_name=name, priority=i + 1)
            for i, name in enumerate(sorted_alts)
        ]

    async def _query_adaptive_module(
        self,
        alternatives: List[str],
    ) -> Dict[str, Dict[str, float]]:
        """Query the adaptive module for historical stability data (async version).

        Args:
            alternatives: List of selector alternatives to query.

        Returns:
            Dictionary mapping selector names to historical stability data.
            Format: {selector_name: {"avg_stability": float, ...}}

        Raises:
            AdaptiveModuleUnavailableError: If adaptive module cannot be accessed.
        """
        try:
            from src.selectors.adaptive.services.stability_scoring import StabilityScoringService

            stability_service = StabilityScoringService()

            result = {}
            for alt in alternatives:
                try:
                    stability_data = await stability_service.get_recipe_stability(alt)
                    if stability_data:
                        result[alt] = {
                            "avg_stability": stability_data.get("stability_score", 0.5)
                        }
                except Exception:
                    pass

            return result

        except ImportError:
            raise AdaptiveModuleUnavailableError(
                message="Adaptive module stability service not available",
                selector_id=None
            )
        except Exception as e:
            raise AdaptiveModuleUnavailableError(
                message=f"Failed to query adaptive module: {str(e)}",
                selector_id=None
            )

    def _query_adaptive_module_sync(
        self,
        alternatives: List[str],
    ) -> Dict[str, Dict[str, float]]:
        """Query the adaptive module for historical stability data (synchronous version).

        Args:
            alternatives: List of selector alternatives to query.

        Returns:
            Dictionary mapping selector names to historical stability data.
            Format: {selector_name: {"avg_stability": float, ...}}

        Raises:
            AdaptiveModuleUnavailableError: If adaptive module cannot be accessed.
        """
        try:
            from src.selectors.adaptive.services.stability_scoring import StabilityScoringService

            stability_service = StabilityScoringService()

            result = {}
            for alt in alternatives:
                try:
                    # Get stability data synchronously - check if there's a sync method
                    # or use run_until_complete for the async method
                    import asyncio
                    try:
                        # Try to get the event loop and run the async method
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # In async context, we can't use run_until_complete
                            # Just skip this selector for now
                            continue
                        else:
                            stability_data = loop.run_until_complete(
                                stability_service.get_recipe_stability(alt)
                            )
                    except RuntimeError:
                        # No event loop, create a new one
                        stability_data = asyncio.run(
                            stability_service.get_recipe_stability(alt)
                        )
                    
                    if stability_data:
                        result[alt] = {
                            "avg_stability": stability_data.get("stability_score", 0.5)
                        }
                except Exception:
                    # If async call fails, try to continue
                    pass

            return result

        except ImportError:
            raise AdaptiveModuleUnavailableError(
                message="Adaptive module stability service not available",
                selector_id=None
            )
        except Exception as e:
            raise AdaptiveModuleUnavailableError(
                message=f"Failed to query adaptive module: {str(e)}",
                selector_id=None
            )

    # ------------------------------------------------------------------
    # Custom rule post-processing
    # ------------------------------------------------------------------

    def _apply_custom_rules(
        self,
        alternatives: List[FallbackConfig],
        metadata: Dict[str, Any],
    ) -> List[FallbackConfig]:
        """Apply custom rules from metadata as a post-processing pass.

        Rules are stored at ``metadata["rules"]`` as a list of dicts::

            [
                {"type": "skip",   "selector": "bad_selector"},
                {"type": "prefer", "selector": "best_selector"},
            ]

        ``"skip"``  – removes the named alternative from the chain.
        ``"prefer"`` – moves the named alternative to the front (highest priority).
        Unrecognised rule types are ignored with a DEBUG log entry.

        After all rules are applied, priorities are reassigned sequentially
        (1, 2, 3, …) to reflect the new ordering.

        Args:
            alternatives: Ordered list of FallbackConfig objects produced by the
                          strategy step.
            metadata: Hint metadata dict containing the ``"rules"`` key.

        Returns:
            Updated FallbackConfig list with priorities re-normalised.
        """
        rules: List[Dict[str, Any]] = metadata.get("rules", [])
        if not rules:
            return alternatives

        result = list(alternatives)

        for rule in rules:
            rule_type = rule.get("type")
            selector_name = rule.get("selector")

            if rule_type == "skip":
                result = [f for f in result if f.selector_name != selector_name]

            elif rule_type == "prefer":
                matched = [f for f in result if f.selector_name == selector_name]
                others = [f for f in result if f.selector_name != selector_name]
                result = matched + others

            else:
                self._logger.debug(
                    "unknown_custom_rule_type_ignored",
                    extra={"rule_type": rule_type, "selector": selector_name},
                )

        # Re-normalise priorities to reflect new ordering
        result = [
            FallbackConfig(
                selector_name=f.selector_name,
                priority=i + 1,
                enabled=f.enabled,
                max_attempts=f.max_attempts,
                timeout_seconds=f.timeout_seconds,
                metadata=f.metadata,
            )
            for i, f in enumerate(result)
        ]

        return result
