"""
Unit tests for HintBasedFallbackStrategy and FallbackChainExecutor.execute_with_hint_strategy.

Tests cover:
- Linear strategy: preserves listed order
- Priority strategy: reorders by per-alternative priority values in metadata
- Stability strategy: orders by stability score from YAML hints (highest first)
- Adaptive strategy: uses historical stability data from adaptive module
- Custom rules: "skip" removes an alternative from the chain
- Custom rules: "prefer" moves an alternative to the front of the chain
- Error: raises SelectorConfigurationError when hint has no alternatives
- Integration: execute_with_hint_strategy delegates to execute_chain via HintBasedFallbackStrategy
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.selectors.exceptions import SelectorConfigurationError, AdaptiveModuleUnavailableError
from src.selectors.fallback.models import FallbackConfig
from src.selectors.hints.models import SelectorHint
from src.selectors.hints.strategy import HintBasedFallbackStrategy

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _names(fallbacks: list) -> list:
    """Return selector_name list from a list of FallbackConfig objects."""
    return [f.selector_name for f in fallbacks]


def _priorities(fallbacks: list) -> list:
    """Return priority list from a list of FallbackConfig objects."""
    return [f.priority for f in fallbacks]


# ---------------------------------------------------------------------------
# TestHintBasedFallbackStrategy – strategy methods
# ---------------------------------------------------------------------------


class TestHintBasedFallbackStrategy:
    """Unit tests for HintBasedFallbackStrategy."""

    # --- linear strategy ---------------------------------------------------

    @pytest.mark.unit
    def test_linear_strategy_preserves_listed_order(self):
        """Linear strategy keeps alternatives in their declared list order."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(alternatives=["fb1", "fb2", "fb3"], strategy="linear")

        chain = strategy.build_chain_from_hint("primary", hint)

        assert _names(chain.fallbacks) == ["fb1", "fb2", "fb3"]

    @pytest.mark.unit
    def test_linear_strategy_assigns_sequential_priorities(self):
        """Linear strategy assigns priorities 1, 2, 3, … matching list order."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(alternatives=["a", "b", "c"], strategy="linear")

        chain = strategy.build_chain_from_hint("primary", hint)

        assert _priorities(chain.fallbacks) == [1, 2, 3]

    @pytest.mark.unit
    def test_linear_strategy_single_alternative(self):
        """Linear strategy works with a single alternative."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(alternatives=["only_fb"], strategy="linear")

        chain = strategy.build_chain_from_hint("primary", hint)

        assert len(chain.fallbacks) == 1
        assert chain.fallbacks[0].selector_name == "only_fb"
        assert chain.fallbacks[0].priority == 1

    # --- priority strategy -------------------------------------------------

    @pytest.mark.unit
    def test_priority_strategy_reorders_by_descending_priority_value(self):
        """Priority strategy sorts alternatives so highest priority value is first."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(
            alternatives=["fb1", "fb2", "fb3"],
            strategy="priority",
            metadata={"priorities": {"fb1": 3, "fb2": 1, "fb3": 2}},
        )

        chain = strategy.build_chain_from_hint("primary", hint)

        # fb1(3) > fb3(2) > fb2(1)
        assert _names(chain.fallbacks) == ["fb1", "fb3", "fb2"]

    @pytest.mark.unit
    def test_priority_strategy_reassigns_chain_priorities_after_sort(self):
        """Priority strategy emits FallbackConfig priorities 1, 2, 3 after reordering."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(
            alternatives=["fb1", "fb2", "fb3"],
            strategy="priority",
            metadata={"priorities": {"fb1": 3, "fb2": 1, "fb3": 2}},
        )

        chain = strategy.build_chain_from_hint("primary", hint)

        assert _priorities(chain.fallbacks) == [1, 2, 3]

    @pytest.mark.unit
    def test_priority_strategy_uses_default_mid_priority_for_missing_entries(self):
        """Alternatives absent from the priorities map receive default priority 5."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(
            alternatives=["fb1", "fb2", "fb3"],
            strategy="priority",
            metadata={"priorities": {"fb1": 8}},  # fb2, fb3 not in map → default 5
        )

        chain = strategy.build_chain_from_hint("primary", hint)

        # fb1(8) is first; fb2(5) and fb3(5) follow (stable sort not required,
        # but both must appear after fb1)
        names = _names(chain.fallbacks)
        assert names[0] == "fb1"
        assert set(names[1:]) == {"fb2", "fb3"}

    @pytest.mark.unit
    def test_priority_strategy_with_no_priorities_map_uses_defaults(self):
        """Priority strategy works when metadata exists but has no 'priorities' key."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(
            alternatives=["fb1", "fb2"],
            strategy="priority",
            metadata={"other_key": "value"},
        )

        chain = strategy.build_chain_from_hint("primary", hint)

        # All equal priority → order may vary, but all alternatives present
        assert set(_names(chain.fallbacks)) == {"fb1", "fb2"}

    @pytest.mark.unit
    def test_priority_strategy_with_none_metadata_uses_defaults(self):
        """Priority strategy handles None metadata gracefully."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(alternatives=["fb1", "fb2"], strategy="priority")
        # metadata is None by default

        chain = strategy.build_chain_from_hint("primary", hint)

        assert set(_names(chain.fallbacks)) == {"fb1", "fb2"}

    # --- adaptive strategy (Story 2-3 implementation) -----------------------

    @pytest.mark.unit
    def test_adaptive_strategy_queries_stability_service(self):
        """Adaptive strategy queries the adaptive module for historical stability data."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(
            alternatives=["fb1", "fb2", "fb3"],
            strategy="adaptive",
            stability=0.5
        )

        # Mock the adaptive module to return historical data
        mock_data = {
            "fb1": {"avg_stability": 0.9},
            "fb2": {"avg_stability": 0.3},
            "fb3": {"avg_stability": 0.7}
        }

        with patch.object(strategy, "_query_adaptive_module_sync", return_value=mock_data):
            chain = strategy.build_chain_from_hint("primary", hint)

        # Should be ordered by merged stability: fb1(0.62) > fb3(0.44) > fb2(0.26)
        # merged = 0.3 * yaml + 0.7 * historical
        # fb1: 0.3*0.5 + 0.7*0.9 = 0.15 + 0.63 = 0.78
        # fb3: 0.3*0.5 + 0.7*0.7 = 0.15 + 0.49 = 0.64
        # fb2: 0.3*0.5 + 0.7*0.3 = 0.15 + 0.21 = 0.36
        assert _names(chain.fallbacks) == ["fb1", "fb3", "fb2"]

    @pytest.mark.unit
    def test_adaptive_strategy_falls_back_to_stability_when_unavailable(self):
        """Adaptive strategy falls back to stability strategy when adaptive module unavailable."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(
            alternatives=["fb1", "fb2"],
            strategy="adaptive",
            stability=0.7,
            metadata={"stability_scores": {"fb1": 0.9, "fb2": 0.5}}
        )

        with patch.object(
            strategy, "_query_adaptive_module_sync",
            side_effect=AdaptiveModuleUnavailableError("Module unavailable")
        ):
            chain = strategy.build_chain_from_hint("primary", hint)

        # Should fall back to stability ordering: fb1(0.9) > fb2(0.5)
        assert _names(chain.fallbacks) == ["fb1", "fb2"]

    @pytest.mark.unit
    def test_adaptive_strategy_uses_yaml_only_when_no_historical_data(self):
        """Adaptive strategy uses YAML stability when no historical data available for selector."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(
            alternatives=["fb1", "fb2"],
            strategy="adaptive",
            stability=0.6
        )

        # Historical data only for fb1
        mock_data = {
            "fb1": {"avg_stability": 0.9}
            # fb2 not in historical data
        }

        with patch.object(strategy, "_query_adaptive_module_sync", return_value=mock_data):
            chain = strategy.build_chain_from_hint("primary", hint)

        # fb1: 0.3*0.6 + 0.7*0.9 = 0.18 + 0.63 = 0.81
        # fb2: 0.3*0.6 + 0.7*0.6 = 0.18 + 0.42 = 0.60 (uses yaml as fallback)
        assert _names(chain.fallbacks) == ["fb1", "fb2"]

    # --- stability strategy (Story 2-3) ---------------------------------------

    @pytest.mark.unit
    def test_stability_strategy_orders_by_stability_highest_first(self):
        """Stability strategy orders alternatives by stability score (highest first)."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(
            alternatives=["fb1", "fb2", "fb3"],
            strategy="stability",
            stability=0.5,
            metadata={"stability_scores": {"fb1": 0.5, "fb2": 0.9, "fb3": 0.7}}
        )

        chain = strategy.build_chain_from_hint("primary", hint)

        # Order: fb2(0.9) > fb3(0.7) > fb1(0.5)
        assert _names(chain.fallbacks) == ["fb2", "fb3", "fb1"]
        assert _priorities(chain.fallbacks) == [1, 2, 3]

    @pytest.mark.unit
    def test_stability_strategy_uses_hint_stability_as_default(self):
        """Stability strategy uses hint.stability as default when no per-alternative score."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(
            alternatives=["fb1", "fb2", "fb3"],
            strategy="stability",
            stability=0.8
            # No stability_scores in metadata - should use 0.8 for all
        )

        chain = strategy.build_chain_from_hint("primary", hint)

        # All have same stability (0.8), order may vary but all present
        assert set(_names(chain.fallbacks)) == {"fb1", "fb2", "fb3"}

    @pytest.mark.unit
    def test_stability_strategy_0_9_over_0_7_over_0_5(self):
        """AC1: Verify 0.9 > 0.7 > 0.5 ordering in fallback chain."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(
            alternatives=["low", "high", "medium"],
            strategy="stability",
            metadata={"stability_scores": {"low": 0.5, "high": 0.9, "medium": 0.7}}
        )

        chain = strategy.build_chain_from_hint("primary", hint)

        assert _names(chain.fallbacks) == ["high", "medium", "low"]

    @pytest.mark.unit
    def test_stability_strategy_single_alternative(self):
        """Stability strategy works with a single alternative."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(
            alternatives=["only_fb"],
            strategy="stability",
            stability=0.9
        )

        chain = strategy.build_chain_from_hint("primary", hint)

        assert len(chain.fallbacks) == 1
        assert chain.fallbacks[0].selector_name == "only_fb"
        assert chain.fallbacks[0].priority == 1

    @pytest.mark.unit
    def test_stability_strategy_with_custom_rules(self):
        """Stability strategy works with custom rules applied after sorting."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(
            alternatives=["fb1", "fb2", "fb3"],
            strategy="stability",
            metadata={
                "stability_scores": {"fb1": 0.7, "fb2": 0.9, "fb3": 0.5},
                "rules": [{"type": "skip", "selector": "fb3"}]
            }
        )

        chain = strategy.build_chain_from_hint("primary", hint)

        # Sorted: fb2(0.9) > fb1(0.7), then skip fb3
        assert _names(chain.fallbacks) == ["fb2", "fb1"]

    # --- SelectorConfigurationError when hint has no alternatives ----------

    @pytest.mark.unit
    def test_raises_configuration_error_when_no_alternatives(self):
        """build_chain_from_hint raises SelectorConfigurationError on empty alternatives."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(alternatives=[], strategy="linear")

        with pytest.raises(SelectorConfigurationError) as exc_info:
            strategy.build_chain_from_hint("primary_sel", hint)

        assert exc_info.value.selector_id == "primary_sel"

    @pytest.mark.unit
    def test_raises_configuration_error_preserves_selector_id(self):
        """The raised SelectorConfigurationError embeds the correct selector ID."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(alternatives=[], strategy="priority")

        with pytest.raises(SelectorConfigurationError) as exc_info:
            strategy.build_chain_from_hint("my_widget_selector", hint)

        assert exc_info.value.selector_id == "my_widget_selector"

    # --- custom rules: skip ------------------------------------------------

    @pytest.mark.unit
    def test_custom_rule_skip_removes_alternative_from_chain(self):
        """'skip' rule removes the named alternative from the fallback chain."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(
            alternatives=["fb1", "fb2", "fb3"],
            strategy="linear",
            metadata={"rules": [{"type": "skip", "selector": "fb2"}]},
        )

        chain = strategy.build_chain_from_hint("primary", hint)

        assert _names(chain.fallbacks) == ["fb1", "fb3"]

    @pytest.mark.unit
    def test_custom_rule_skip_renormalises_priorities(self):
        """After 'skip', remaining FallbackConfigs have sequential priorities."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(
            alternatives=["fb1", "fb2", "fb3"],
            strategy="linear",
            metadata={"rules": [{"type": "skip", "selector": "fb1"}]},
        )

        chain = strategy.build_chain_from_hint("primary", hint)

        assert _priorities(chain.fallbacks) == [1, 2]

    @pytest.mark.unit
    def test_custom_rule_skip_nonexistent_selector_is_noop(self):
        """Skipping a selector not in the alternatives list leaves chain unchanged."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(
            alternatives=["fb1", "fb2"],
            strategy="linear",
            metadata={"rules": [{"type": "skip", "selector": "not_present"}]},
        )

        chain = strategy.build_chain_from_hint("primary", hint)

        assert _names(chain.fallbacks) == ["fb1", "fb2"]

    # --- custom rules: prefer ----------------------------------------------

    @pytest.mark.unit
    def test_custom_rule_prefer_moves_alternative_to_front(self):
        """'prefer' rule moves the named alternative to the front of the chain."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(
            alternatives=["fb1", "fb2", "fb3"],
            strategy="linear",
            metadata={"rules": [{"type": "prefer", "selector": "fb3"}]},
        )

        chain = strategy.build_chain_from_hint("primary", hint)

        assert chain.fallbacks[0].selector_name == "fb3"

    @pytest.mark.unit
    def test_custom_rule_prefer_preserves_remaining_order(self):
        """After 'prefer', the rest of the chain retains its relative order."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(
            alternatives=["fb1", "fb2", "fb3"],
            strategy="linear",
            metadata={"rules": [{"type": "prefer", "selector": "fb3"}]},
        )

        chain = strategy.build_chain_from_hint("primary", hint)

        assert _names(chain.fallbacks) == ["fb3", "fb1", "fb2"]

    @pytest.mark.unit
    def test_custom_rule_prefer_renormalises_priorities(self):
        """After 'prefer', FallbackConfigs have sequential priorities from the new front."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(
            alternatives=["fb1", "fb2", "fb3"],
            strategy="linear",
            metadata={"rules": [{"type": "prefer", "selector": "fb2"}]},
        )

        chain = strategy.build_chain_from_hint("primary", hint)

        assert _priorities(chain.fallbacks) == [1, 2, 3]
        assert chain.fallbacks[0].selector_name == "fb2"

    # --- custom rules: combined skip + prefer ------------------------------

    @pytest.mark.unit
    def test_combined_skip_and_prefer_rules_applied_in_order(self):
        """Multiple custom rules are applied sequentially in declaration order."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(
            alternatives=["fb1", "fb2", "fb3", "fb4"],
            strategy="linear",
            metadata={
                "rules": [
                    {"type": "skip", "selector": "fb1"},
                    {"type": "prefer", "selector": "fb4"},
                ]
            },
        )

        chain = strategy.build_chain_from_hint("primary", hint)

        # fb1 removed; fb4 moved to front → [fb4, fb2, fb3]
        assert _names(chain.fallbacks) == ["fb4", "fb2", "fb3"]
        assert _priorities(chain.fallbacks) == [1, 2, 3]

    # --- custom rules: unrecognised type -----------------------------------

    @pytest.mark.unit
    def test_unrecognised_custom_rule_type_is_ignored(self):
        """An unrecognised rule type leaves the chain unchanged (logged at DEBUG)."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(
            alternatives=["fb1", "fb2"],
            strategy="linear",
            metadata={"rules": [{"type": "unknown_rule", "selector": "fb1"}]},
        )

        chain = strategy.build_chain_from_hint("primary", hint)

        # Chain is unchanged
        assert _names(chain.fallbacks) == ["fb1", "fb2"]

    @pytest.mark.unit
    def test_unrecognised_custom_rule_logs_debug(self):
        """An unrecognised rule type triggers a DEBUG log entry."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(
            alternatives=["fb1"],
            strategy="linear",
            metadata={"rules": [{"type": "bogus", "selector": "fb1"}]},
        )

        with patch.object(strategy, "_logger") as mock_logger:
            strategy.build_chain_from_hint("primary", hint)

        mock_logger.debug.assert_called()

    # --- custom rules applied to priority / adaptive strategies -----------

    @pytest.mark.unit
    def test_custom_rules_applied_after_priority_strategy(self):
        """Custom rules are a post-processing pass regardless of declared strategy."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(
            alternatives=["fb1", "fb2", "fb3"],
            strategy="priority",
            metadata={
                "priorities": {"fb1": 3, "fb2": 2, "fb3": 1},
                "rules": [{"type": "skip", "selector": "fb1"}],
            },
        )

        chain = strategy.build_chain_from_hint("primary", hint)

        # Priority order before skip: fb1, fb2, fb3 → skip fb1 → fb2, fb3
        assert _names(chain.fallbacks) == ["fb2", "fb3"]

    # --- max_duration propagated to chain ----------------------------------

    @pytest.mark.unit
    def test_build_chain_propagates_max_duration(self):
        """max_duration is correctly set on the produced FallbackChain."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(alternatives=["fb1"], strategy="linear")

        chain = strategy.build_chain_from_hint("primary", hint, max_duration=2.5)

        assert chain.max_chain_duration == 2.5

    @pytest.mark.unit
    def test_build_chain_default_max_duration_is_five_seconds(self):
        """Default max_duration is 5.0 seconds (NFR1)."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(alternatives=["fb1"], strategy="linear")

        chain = strategy.build_chain_from_hint("primary", hint)

        assert chain.max_chain_duration == 5.0

    # --- primary selector stored in chain ----------------------------------

    @pytest.mark.unit
    def test_build_chain_stores_primary_selector_name(self):
        """The produced FallbackChain contains the correct primary selector."""
        strategy = HintBasedFallbackStrategy()
        hint = SelectorHint(alternatives=["fb1"], strategy="linear")

        chain = strategy.build_chain_from_hint("my_primary", hint)

        assert chain.primary_selector == "my_primary"


# ---------------------------------------------------------------------------
# TestExecuteWithHintStrategy – executor integration
# ---------------------------------------------------------------------------


class TestExecuteWithHintStrategy:
    """Integration tests for FallbackChainExecutor.execute_with_hint_strategy."""

    def _make_success_result(self):
        """Create a mock SelectorResult that represents success."""
        result = MagicMock()
        result.success = True
        result.element_info = MagicMock()
        result.element_info.text_content = "value"
        result.confidence_score = 0.9
        result.failure_reason = None
        result.resolution_time = 0.01
        return result

    def _make_failure_result(self, reason: str = "not found"):
        """Create a mock SelectorResult that represents failure."""
        result = MagicMock()
        result.success = False
        result.element_info = None
        result.confidence_score = 0.0
        result.failure_reason = reason
        result.resolution_time = 0.01
        return result

    def _make_context(self, url: str = "http://test.com"):
        """Create a lightweight mock DOMContext."""
        from src.selectors.context import DOMContext

        ctx = MagicMock(spec=DOMContext)
        ctx.url = url
        ctx.tab_context = None
        ctx.metadata = {}
        return ctx

    # --- primary succeeds (no fallback triggered) --------------------------

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_primary_success_no_fallback_triggered(self):
        """When primary succeeds, fallback_executed is False."""
        from src.selectors.fallback.chain import FallbackChainExecutor

        mock_engine = MagicMock()
        mock_engine.resolve = AsyncMock(return_value=self._make_success_result())

        executor = FallbackChainExecutor(selector_engine=mock_engine)
        hint = SelectorHint(alternatives=["fallback1"], strategy="linear")
        context = self._make_context()

        result = await executor.execute_with_hint_strategy("primary", hint, context)

        assert result.primary_success is True
        assert result.fallback_executed is False

    # --- primary fails, fallback succeeds ----------------------------------

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_primary_fails_fallback_succeeds(self):
        """When primary fails, the hint alternative is executed and succeeds."""
        from src.selectors.fallback.chain import FallbackChainExecutor

        mock_engine = MagicMock()
        mock_engine.resolve = AsyncMock(
            side_effect=[
                self._make_failure_result("not found"),
                self._make_success_result(),
            ]
        )

        executor = FallbackChainExecutor(selector_engine=mock_engine)
        hint = SelectorHint(alternatives=["fallback1"], strategy="linear")
        context = self._make_context()

        result = await executor.execute_with_hint_strategy("primary", hint, context)

        assert result.fallback_executed is True
        assert result.fallback_success is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_uses_hint_alternatives_in_linear_order(self):
        """execute_with_hint_strategy tries alternatives in listed order."""
        from src.selectors.fallback.chain import FallbackChainExecutor

        resolve_calls: list = []

        async def _track_resolve(selector_name, context):
            resolve_calls.append(selector_name)
            if selector_name == "primary":
                return self._make_failure_result()
            if selector_name == "fb1":
                return self._make_failure_result()
            return self._make_success_result()

        mock_engine = MagicMock()
        mock_engine.resolve = AsyncMock(side_effect=_track_resolve)

        executor = FallbackChainExecutor(selector_engine=mock_engine)
        hint = SelectorHint(alternatives=["fb1", "fb2"], strategy="linear")
        context = self._make_context()

        result = await executor.execute_with_hint_strategy("primary", hint, context)

        assert resolve_calls == ["primary", "fb1", "fb2"]
        assert result.fallback_success is True

    # --- primary fails, all fallbacks fail ---------------------------------

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_all_fallbacks_fail_returns_failure_result(self):
        """When all fallbacks fail, fallback_success is False."""
        from src.selectors.fallback.chain import FallbackChainExecutor

        mock_engine = MagicMock()
        mock_engine.resolve = AsyncMock(
            side_effect=[
                self._make_failure_result("primary not found"),
                self._make_failure_result("fb1 not found"),
            ]
        )

        executor = FallbackChainExecutor(selector_engine=mock_engine)
        hint = SelectorHint(alternatives=["fb1"], strategy="linear")
        context = self._make_context()

        result = await executor.execute_with_hint_strategy("primary", hint, context)

        assert result.fallback_executed is True
        assert result.fallback_success is False

    # --- empty alternatives raises error before any network call -----------

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_empty_alternatives_raises_configuration_error(self):
        """execute_with_hint_strategy raises SelectorConfigurationError for empty hint."""
        from src.selectors.fallback.chain import FallbackChainExecutor

        mock_engine = MagicMock()
        mock_engine.resolve = AsyncMock(return_value=self._make_success_result())

        executor = FallbackChainExecutor(selector_engine=mock_engine)
        hint = SelectorHint(alternatives=[], strategy="linear")
        context = self._make_context()

        with pytest.raises(SelectorConfigurationError):
            await executor.execute_with_hint_strategy("primary", hint, context)

        # Engine should NOT have been called
        mock_engine.resolve.assert_not_called()

    # --- strategy is logged at debug level ---------------------------------

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_logs_strategy_at_debug(self):
        """execute_with_hint_strategy logs which strategy was applied."""
        from src.selectors.fallback.chain import FallbackChainExecutor

        mock_engine = MagicMock()
        mock_engine.resolve = AsyncMock(return_value=self._make_success_result())

        executor = FallbackChainExecutor(selector_engine=mock_engine)
        hint = SelectorHint(alternatives=["fallback1"], strategy="linear")
        context = self._make_context()

        with patch.object(executor, "_logger") as mock_logger:
            await executor.execute_with_hint_strategy("primary", hint, context)

        mock_logger.debug.assert_called()

    # --- priority strategy routing -----------------------------------------

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_priority_strategy_uses_reordered_alternatives(self):
        """execute_with_hint_strategy respects priority reordering from metadata."""
        from src.selectors.fallback.chain import FallbackChainExecutor

        resolve_calls: list = []

        async def _track_resolve(selector_name, context):
            resolve_calls.append(selector_name)
            if selector_name == "primary":
                return self._make_failure_result()
            return self._make_success_result()

        mock_engine = MagicMock()
        mock_engine.resolve = AsyncMock(side_effect=_track_resolve)

        executor = FallbackChainExecutor(selector_engine=mock_engine)
        hint = SelectorHint(
            alternatives=["fb_low", "fb_high"],
            strategy="priority",
            metadata={"priorities": {"fb_low": 1, "fb_high": 10}},
        )
        context = self._make_context()

        await executor.execute_with_hint_strategy("primary", hint, context)

        # fb_high (priority 10) should be tried before fb_low (priority 1)
        assert resolve_calls[1] == "fb_high"

    # --- adaptive strategy routes to linear --------------------------------

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_adaptive_strategy_executes_linearly(self):
        """execute_with_hint_strategy with adaptive strategy falls back to linear."""
        from src.selectors.fallback.chain import FallbackChainExecutor

        resolve_calls: list = []

        async def _track_resolve(selector_name, context):
            resolve_calls.append(selector_name)
            if selector_name == "primary":
                return self._make_failure_result()
            return self._make_success_result()

        mock_engine = MagicMock()
        mock_engine.resolve = AsyncMock(side_effect=_track_resolve)

        executor = FallbackChainExecutor(selector_engine=mock_engine)
        hint = SelectorHint(alternatives=["fb1", "fb2"], strategy="adaptive")
        context = self._make_context()

        result = await executor.execute_with_hint_strategy("primary", hint, context)

        # Should have tried primary then fb1 (first in linear order)
        assert resolve_calls[0] == "primary"
        assert resolve_calls[1] == "fb1"
        assert result.fallback_success is True
