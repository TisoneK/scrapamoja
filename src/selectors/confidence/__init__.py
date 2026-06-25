"""
Confidence management components for Selector Engine.

This module provides confidence threshold management, validation rules,
and quality control automation as specified in the API contracts.
"""

from .thresholds import ConfidenceThresholdManager, get_threshold_manager

# Re-export ConfidenceScorer from the standalone confidence.py module.
# The directory src/selectors/confidence/ shadows the file src/selectors/confidence.py,
# so we manually load and re-export the class to preserve backward compatibility.
import importlib.util
import os as _os

_confidence_py_path = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "confidence.py")
if _os.path.exists(_confidence_py_path):
    _spec = importlib.util.spec_from_file_location(
        "selectors._confidence_standalone", _confidence_py_path
    )
    if _spec and _spec.loader:
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        ConfidenceScorer = _mod.ConfidenceScorer
        get_confidence_scorer = _mod.get_confidence_scorer
        ConfidenceWeights = _mod.ConfidenceWeights
        ScoringContext = _mod.ScoringContext

__all__ = [
    "ConfidenceThresholdManager",
    "get_threshold_manager",
    "ConfidenceScorer",
    "get_confidence_scorer",
    "ConfidenceWeights",
    "ScoringContext",
]
