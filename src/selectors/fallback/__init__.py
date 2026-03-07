"""
Fallback selector module for automatic fallback resolution.

This module provides fallback chain execution when primary selectors fail,
supporting the automatic fallback resolution feature as specified in Epic 1.

Exports:
    FallbackChainExecutor: Main executor for fallback chain logic
    create_fallback_chain: Helper function to create fallback chains
    with_fallback: Decorator for declarative fallback chain definition
    create_fallback_decorator: Factory for creating reusable fallback decorators
    models: Fallback-specific data models
    logging: Fallback attempt logging module
"""

from src.selectors.fallback.chain import FallbackChainExecutor, create_fallback_chain
from src.selectors.fallback.decorator import with_fallback, create_fallback_decorator
from src.selectors.fallback import models
from src.selectors.fallback import logging

__all__ = [
    "FallbackChainExecutor",
    "create_fallback_chain",
    "with_fallback",
    "create_fallback_decorator",
    "models",
    "logging",
]
