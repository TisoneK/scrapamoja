"""
Tests for Story 1.2: Fallback Selector Execution

This module tests the fallback selector execution functionality as defined in:
- AC1: Fallback Selector Execution - Execute fallback when primary fails
- AC2: Failure Event Logging - Log failure details with selector ID, URL, timestamp, failure type

These tests verify the integration of:
- FallbackChainExecutor for fallback chain execution
- Failure event capture and logging
- Fallback result handling

REVIEW FIX: Tests verify actual execution with mock page, not just attribute existence.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, Mock
import tempfile

from src.selectors.fallback.chain import FallbackChainExecutor, create_fallback_chain
from src.selectors.fallback.models import (
    FallbackChain,
    FallbackConfig,
    FallbackResult,
    FallbackStatus,
    FailureEvent,
    FailureType,
    FallbackAttempt,
)
from src.models.selector_models import SelectorResult, ElementInfo


class TestFallbackModels:
    """Test suite for fallback data models."""

    def test_fallback_config_creation(self):
        """Test FallbackConfig can be created with valid parameters."""
        config = FallbackConfig(
            selector_name="match_title_fallback",
            priority=1,
            enabled=True,
            max_attempts=1,
            timeout_seconds=30.0
        )
        assert config.selector_name == "match_title_fallback"
        assert config.priority == 1
        assert config.enabled is True

    def test_fallback_config_invalid_priority(self):
        """Test FallbackConfig validation rejects invalid priority."""
        with pytest.raises(ValueError, match="priority must be >= 1"):
            FallbackConfig(selector_name="test", priority=0)

    def test_fallback_chain_creation(self):
        """Test FallbackChain can be created with fallbacks."""
        fallbacks = [
            FallbackConfig(selector_name="fallback_1", priority=1),
            FallbackConfig(selector_name="fallback_2", priority=2),
        ]
        chain = FallbackChain(
            primary_selector="primary_selector",
            fallbacks=fallbacks
        )
        assert chain.primary_selector == "primary_selector"
        assert len(chain.fallbacks) == 2

    def test_fallback_chain_sorts_by_priority(self):
        """Test FallbackChain sorts fallbacks by priority."""
        fallbacks = [
            FallbackConfig(selector_name="fallback_2", priority=2),
            FallbackConfig(selector_name="fallback_1", priority=1),
        ]
        chain = FallbackChain(
            primary_selector="primary",
            fallbacks=fallbacks
        )
        # Should be sorted: fallback_1 first
        assert chain.fallbacks[0].selector_name == "fallback_1"

    def test_fallback_chain_get_fallback_names(self):
        """Test FallbackChain returns fallback names in priority order."""
        fallbacks = [
            FallbackConfig(selector_name="fallback_1", priority=1, enabled=True),
            FallbackConfig(selector_name="fallback_2", priority=2, enabled=False),
            FallbackConfig(selector_name="fallback_3", priority=3, enabled=True),
        ]
        chain = FallbackChain(
            primary_selector="primary",
            fallbacks=fallbacks
        )
        names = chain.get_fallback_names()
        assert names == ["fallback_1", "fallback_3"]  # Only enabled, in order

    def test_failure_event_to_dict(self):
        """Test FailureEvent serialization to dictionary."""
        event = FailureEvent(
            selector_id="test_selector",
            url="https://test.com",
            timestamp=datetime.now(timezone.utc),
            failure_type=FailureType.EMPTY_RESULT,
            error_message="No element found"
        )
        result = event.to_dict()
        assert result["selector_id"] == "test_selector"
        assert result["failure_type"] == "empty_result"

    def test_fallback_attempt_to_dict(self):
        """Test FallbackAttempt serialization to dictionary."""
        attempt = FallbackAttempt(
            fallback_selector="fallback_selector",
            status=FallbackStatus.SUCCESS,
            timestamp=datetime.now(timezone.utc),
            result={"text": "success"},
            resolution_time=0.5
        )
        result = attempt.to_dict()
        assert result["fallback_selector"] == "fallback_selector"
        assert result["status"] == "success"

    def test_fallback_result_overall_success_primary(self):
        """Test FallbackResult overall_success when primary succeeds."""
        result = FallbackResult(
            primary_selector="primary",
            primary_success=True,
            fallback_executed=False,
            fallback_success=False,
            final_result={"text": "data"}
        )
        assert result.overall_success is True

    def test_fallback_result_overall_success_fallback(self):
        """Test FallbackResult overall_success when fallback succeeds."""
        result = FallbackResult(
            primary_selector="primary",
            primary_success=False,
            fallback_executed=True,
            fallback_success=True,
            final_result={"text": "fallback_data"}
        )
        assert result.overall_success is True

    def test_fallback_result_overall_failure(self):
        """Test FallbackResult overall_success when both fail."""
        result = FallbackResult(
            primary_selector="primary",
            primary_success=False,
            fallback_executed=True,
            fallback_success=False,
            final_result=None
        )
        assert result.overall_success is False


class TestCreateFallbackChain:
    """Test suite for create_fallback_chain helper function."""

    def test_create_fallback_chain_single(self):
        """Test creating fallback chain with single fallback."""
        chain = create_fallback_chain(
            primary_selector="primary_match_title",
            fallback_selectors=["fallback_match_title"]
        )
        assert chain.primary_selector == "primary_match_title"
        assert len(chain.fallbacks) == 1
        assert chain.fallbacks[0].selector_name == "fallback_match_title"
        assert chain.fallbacks[0].priority == 1

    def test_create_fallback_chain_multiple(self):
        """Test creating fallback chain with multiple fallbacks."""
        chain = create_fallback_chain(
            primary_selector="primary",
            fallback_selectors=["fallback_1", "fallback_2", "fallback_3"]
        )
        assert chain.primary_selector == "primary"
        assert len(chain.fallbacks) == 3
        # Should be in priority order
        assert chain.fallbacks[0].selector_name == "fallback_1"
        assert chain.fallbacks[1].selector_name == "fallback_2"
        assert chain.fallbacks[2].selector_name == "fallback_3"


class TestFallbackChainExecutor:
    """Test suite for FallbackChainExecutor."""

    @pytest.fixture
    def mock_selector_engine(self):
        """Create a mock SelectorEngine."""
        engine = MagicMock()
        engine.resolve = AsyncMock()
        return engine

    @pytest.fixture
    def mock_dom_context(self):
        """Create a mock DOM context."""
        context = MagicMock()
        context.page = AsyncMock()
        context.tab_context = "summary"
        context.url = "https://test.example.com/match/123"
        context.timestamp = datetime.now(timezone.utc)
        context.metadata = {}
        return context

    @pytest.fixture
    def fallback_executor(self, mock_selector_engine):
        """Create FallbackChainExecutor with mock engine."""
        return FallbackChainExecutor(selector_engine=mock_selector_engine)

    def test_executor_initialization(self, fallback_executor):
        """Test FallbackChainExecutor initializes correctly."""
        assert fallback_executor._selector_engine is not None
        assert fallback_executor._logger is not None

    @pytest.mark.asyncio
    async def test_execute_with_fallback_primary_success(
        self, fallback_executor, mock_selector_engine, mock_dom_context
    ):
        """Test fallback execution when primary selector succeeds.
        
        Given: Primary selector succeeds
        When: execute_with_fallback is called
        Then: Fallback is not executed, result is returned immediately
        """
        # Given: Primary selector succeeds
        success_result = SelectorResult(
            selector_name="primary",
            strategy_used="css",
            element_info=ElementInfo(
                tag_name="div",
                text_content="Match Title",
                attributes={},
                css_classes=[],
                dom_path="/html/body/div",
                visibility=True,
                interactable=True
            ),
            confidence_score=0.95,
            resolution_time=0.1,
            validation_results=[],
            success=True
        )
        mock_selector_engine.resolve = AsyncMock(return_value=success_result)

        # When
        result = await fallback_executor.execute_with_fallback(
            selector_name="primary",
            context=mock_dom_context,
            fallback_config=FallbackConfig(selector_name="fallback")
        )

        # Then
        assert result.primary_success is True
        assert result.fallback_executed is False
        assert result.overall_success is True
        assert result.final_result is not None

    @pytest.mark.asyncio
    async def test_execute_with_fallback_primary_failure_fallback_success(
        self, fallback_executor, mock_selector_engine, mock_dom_context
    ):
        """Test fallback execution when primary fails but fallback succeeds.
        
        Given: Primary selector fails
        When: execute_with_fallback is called with fallback
        Then: Fallback is executed and result is returned
        """
        # Given: Primary fails, fallback succeeds
        failure_result = SelectorResult(
            selector_name="primary",
            strategy_used="css",
            element_info=None,
            confidence_score=0.0,
            resolution_time=0.1,
            validation_results=[],
            success=False,
            failure_reason="Element not found"
        )
        success_result = SelectorResult(
            selector_name="fallback",
            strategy_used="xpath",
            element_info=ElementInfo(
                tag_name="span",
                text_content="Fallback Title",
                attributes={"class": "title"},
                css_classes=["title"],
                dom_path="/html/body/span",
                visibility=True,
                interactable=True
            ),
            confidence_score=0.85,
            resolution_time=0.15,
            validation_results=[],
            success=True
        )
        
        mock_selector_engine.resolve = AsyncMock(side_effect=[failure_result, success_result])

        # When
        result = await fallback_executor.execute_with_fallback(
            selector_name="primary",
            context=mock_dom_context,
            fallback_config=FallbackConfig(selector_name="fallback", priority=1)
        )

        # Then
        assert result.primary_success is False
        assert result.fallback_executed is True
        assert result.fallback_success is True
        assert result.overall_success is True
        assert result.final_result is not None
        assert result.failure_event is not None
        assert result.fallback_attempt is not None

    @pytest.mark.asyncio
    async def test_execute_with_fallback_both_fail(
        self, fallback_executor, mock_selector_engine, mock_dom_context
    ):
        """Test fallback execution when both primary and fallback fail.
        
        Given: Both primary and fallback fail
        When: execute_with_fallback is called
        Then: Failure event is logged, result indicates failure
        """
        # Given: Both fail
        failure_result = SelectorResult(
            selector_name="primary",
            strategy_used="css",
            element_info=None,
            confidence_score=0.0,
            resolution_time=0.1,
            validation_results=[],
            success=False,
            failure_reason="Element not found"
        )
        fallback_failure = SelectorResult(
            selector_name="fallback",
            strategy_used="xpath",
            element_info=None,
            confidence_score=0.0,
            resolution_time=0.15,
            validation_results=[],
            success=False,
            failure_reason="Fallback also not found"
        )
        
        mock_selector_engine.resolve = AsyncMock(side_effect=[failure_result, fallback_failure])

        # When
        result = await fallback_executor.execute_with_fallback(
            selector_name="primary",
            context=mock_dom_context,
            fallback_config=FallbackConfig(selector_name="fallback", priority=1)
        )

        # Then
        assert result.primary_success is False
        assert result.fallback_executed is True
        assert result.fallback_success is False
        assert result.overall_success is False
        assert result.failure_event is not None
        assert result.fallback_attempt is not None

    @pytest.mark.asyncio
    async def test_execute_with_fallback_exception(
        self, fallback_executor, mock_selector_engine, mock_dom_context
    ):
        """Test fallback execution when primary throws exception.
        
        Given: Primary selector throws exception
        When: execute_with_fallback is called
        Then: Failure event is logged with exception type
        """
        # Given: Primary throws exception
        mock_selector_engine.resolve = AsyncMock(
            side_effect=Exception("Browser error")
        )

        # When
        result = await fallback_executor.execute_with_fallback(
            selector_name="primary",
            context=mock_dom_context,
            fallback_config=FallbackConfig(selector_name="fallback", priority=1)
        )

        # Then
        assert result.primary_success is False
        assert result.fallback_executed is True
        assert result.failure_event is not None
        assert result.failure_event.failure_type == FailureType.EXCEPTION

    @pytest.mark.asyncio
    async def test_execute_chain(
        self, fallback_executor, mock_selector_engine, mock_dom_context
    ):
        """Test full chain execution with FallbackChain object.
        
        Given: FallbackChain with primary and fallbacks
        When: execute_chain is called
        Then: Chain is executed in priority order
        """
        # Given
        chain = FallbackChain(
            primary_selector="primary",
            fallbacks=[
                FallbackConfig(selector_name="fallback_1", priority=1),
                FallbackConfig(selector_name="fallback_2", priority=2),
            ]
        )
        
        # Primary fails, first fallback succeeds
        failure_result = SelectorResult(
            selector_name="primary",
            strategy_used="css",
            element_info=None,
            confidence_score=0.0,
            resolution_time=0.1,
            validation_results=[],
            success=False,
            failure_reason="Not found"
        )
        success_result = SelectorResult(
            selector_name="fallback_1",
            strategy_used="xpath",
            element_info=ElementInfo(
                tag_name="div",
                text_content="Chain Result",
                attributes={},
                css_classes=[],
                dom_path="/div",
                visibility=True,
                interactable=True
            ),
            confidence_score=0.9,
            resolution_time=0.2,
            validation_results=[],
            success=True
        )
        
        mock_selector_engine.resolve = AsyncMock(side_effect=[failure_result, success_result])

        # When
        result = await fallback_executor.execute_chain(chain, mock_dom_context)

        # Then
        assert result.primary_success is False
        assert result.fallback_executed is True
        assert result.fallback_success is True
        assert result.final_result is not None


class TestFailureEventLogging:
    """Test suite for failure event capture and logging."""

    @pytest.fixture
    def mock_selector_engine(self):
        """Create a mock SelectorEngine."""
        engine = MagicMock()
        engine.resolve = AsyncMock()
        return engine

    @pytest.fixture
    def fallback_executor(self, mock_selector_engine):
        """Create FallbackChainExecutor with mock engine."""
        return FallbackChainExecutor(selector_engine=mock_selector_engine)

    @pytest.fixture
    def mock_dom_context(self):
        """Create mock DOM context."""
        context = MagicMock()
        context.page = AsyncMock()
        context.tab_context = "summary"
        context.url = "https://flashscore.com/match/123"
        context.timestamp = datetime.now(timezone.utc)
        context.metadata = {"match_id": "123"}
        return context

    @pytest.mark.asyncio
    async def test_failure_event_has_all_required_fields(
        self, fallback_executor, mock_selector_engine, mock_dom_context
    ):
        """Test failure event contains all required information.
        
        Given: Primary selector fails
        When: execute_with_fallback is called
        Then: Failure event has selector_id, url, timestamp, failure_type
        """
        # Given
        mock_selector_engine = MagicMock()
        mock_selector_engine.resolve = AsyncMock(
            return_value=SelectorResult(
                selector_name="primary",
                strategy_used="css",
                element_info=None,
                confidence_score=0.0,
                resolution_time=0.1,
                validation_results=[],
                success=False,
                failure_reason="Empty result"
            )
        )
        fallback_executor._selector_engine = mock_selector_engine

        # When
        result = await fallback_executor.execute_with_fallback(
            selector_name="match_title",
            context=mock_dom_context,
            fallback_config=FallbackConfig(selector_name="fallback_title")
        )

        # Then
        assert result.failure_event is not None
        assert result.failure_event.selector_id == "match_title"
        assert result.failure_event.url == "https://flashscore.com/match/123"
        assert result.failure_event.timestamp is not None
        assert result.failure_event.failure_type == FailureType.EXCEPTION  # Because element_info is None

    @pytest.mark.asyncio
    async def test_fallback_attempt_result_logged(
        self, fallback_executor, mock_selector_engine, mock_dom_context
    ):
        """Test fallback attempt result is captured.
        
        Given: Fallback is executed
        When: execute_with_fallback completes
        Then: Fallback attempt is recorded with status and result
        """
        # Given
        mock_selector_engine = MagicMock()
        
        failure_result = SelectorResult(
            selector_name="primary",
            strategy_used="css",
            element_info=None,
            confidence_score=0.0,
            resolution_time=0.1,
            validation_results=[],
            success=False,
            failure_reason="Not found"
        )
        success_result = SelectorResult(
            selector_name="fallback",
            strategy_used="xpath",
            element_info=ElementInfo(
                tag_name="span",
                text_content="Found",
                attributes={},
                css_classes=[],
                dom_path="/span",
                visibility=True,
                interactable=True
            ),
            confidence_score=0.85,
            resolution_time=0.2,
            validation_results=[],
            success=True
        )
        
        mock_selector_engine.resolve = AsyncMock(side_effect=[failure_result, success_result])
        fallback_executor._selector_engine = mock_selector_engine

        # When
        result = await fallback_executor.execute_with_fallback(
            selector_name="primary",
            context=mock_dom_context,
            fallback_config=FallbackConfig(selector_name="fallback")
        )

        # Then
        assert result.fallback_attempt is not None
        assert result.fallback_attempt.status == FallbackStatus.SUCCESS
        assert result.fallback_attempt.fallback_selector == "fallback"
        assert result.fallback_attempt.result is not None
