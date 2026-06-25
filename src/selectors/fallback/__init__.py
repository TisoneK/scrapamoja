"""
Fallback selector module for automatic fallback resolution.

This module provides fallback chain execution when primary selectors fail,
supporting the automatic fallback resolution feature as specified in Epic 1.

Exports:
    FallbackChainExecutor: Main executor for fallback chain logic.
        Key methods:
            - execute_with_fallback: Single fallback execution with explicit config
            - execute_chain: Full multi-level fallback chain execution
            - execute_with_hint_strategy: Hint-driven chain execution (Story 2-2).
              Builds a FallbackChain from a SelectorHint via HintBasedFallbackStrategy
              and delegates execution to execute_chain(). Use this when YAML selector
              hints define the fallback strategy and alternatives.
    create_fallback_chain: Helper function to create fallback chains
    with_fallback: Decorator for declarative fallback chain definition
    create_fallback_decorator: Factory for creating reusable fallback decorators
    models: Fallback-specific data models
    logging: Fallback attempt logging module
"""

from src.selectors.fallback import logging, models
from src.selectors.fallback.chain import FallbackChainExecutor, create_fallback_chain
from src.selectors.fallback.decorator import create_fallback_decorator, with_fallback

__all__ = [
    "FallbackChainExecutor",
    "create_fallback_chain",
    "with_fallback",
    "create_fallback_decorator",
    "models",
    "logging",
]
