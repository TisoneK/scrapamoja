"""
Selector Engine - Semantic selector resolution with multi-strategy fallback.

This module provides the core components for semantic selector resolution including
strategy patterns, confidence scoring, validation, and the main selector engine.
"""

from .engine import SelectorEngine, get_selector_engine
from .registry import SelectorRegistry, get_selector_registry
from .validation import ValidationEngine, get_validation_engine
# from .confidence import ConfidenceScorer  # TODO: Implement ConfidenceScorer
from .context import DOMContext, ElementInfoExtractor, TabContextManager
from .unified_context import (
    UnifiedContext,
    from_selector_context,
    from_dom_context,
    create_unified_context,
    UnifiedContextError,
    ContextConversionError,
    ContextValidationError
)
from .interfaces import (
    ISelectorEngine, IStrategyPattern, IConfidenceScorer,
    IDOMSnapshotManager, IDriftDetector, IStrategyEvolution
)

# Strategy patterns
from .strategies import (
    BaseStrategyPattern, StrategyFactory,
    TextAnchorStrategy, AttributeMatchStrategy,
    DOMRelationshipStrategy, RoleBasedStrategy
)

__all__ = [
    # Core engine
    "SelectorEngine",
    "get_selector_engine",
    
    # Registry
    "SelectorRegistry",
    "get_selector_registry",
    
    # Confidence scoring
    # "ConfidenceScorer",
    # "get_confidence_scorer",
    
    # Validation
    "ValidationEngine",
    "get_validation_engine",
    
    # Context
    "DOMContext",
    "ElementInfoExtractor",
    "TabContextManager",
    
    # Unified Context
    "UnifiedContext",
    "from_selector_context",
    "from_dom_context",
    "create_unified_context",
    "UnifiedContextError",
    "ContextConversionError",
    "ContextValidationError",
    
    # Interfaces
    "ISelectorEngine",
    "IStrategyPattern",
    "IConfidenceScorer",
    "IDOMSnapshotManager",
    "IDriftDetector",
    "IStrategyEvolution",
    
    # Strategy patterns
    "BaseStrategyPattern",
    "StrategyFactory",
    "TextAnchorStrategy",
    "AttributeMatchStrategy",
    "DOMRelationshipStrategy",
    "RoleBasedStrategy"
]
