"""
Data models for selector hints.

This module defines the data models for selector hints, including:
- SelectorHint: Represents a single selector's hint information
- HintSchema: Schema for validating YAML hint fields

These models are used to deserialize and validate hint information
from YAML selector configurations.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

VALID_STRATEGIES = frozenset({"linear", "priority", "adaptive", "stability"})


@dataclass
class SelectorHint:
    """Represents a selector's hint information.

    Hints provide metadata about selectors that influence fallback chain
    behavior, including stability scores, priorities, alternative selectors,
    and the strategy used to order those alternatives.
    """

    stability: float = 0.5
    priority: int = 5
    alternatives: List[str] = field(default_factory=list)
    strategy: str = "linear"
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate hint values after initialization."""
        if not (0.0 <= self.stability <= 1.0):
            raise ValueError("Stability must be between 0.0 and 1.0")
        if self.priority < 1 or self.priority > 10:
            raise ValueError("Priority must be between 1 and 10")
        if not isinstance(self.alternatives, list):
            raise ValueError("Alternatives must be a list")
        if self.metadata is not None and not isinstance(self.metadata, dict):
            raise ValueError("Metadata must be a dictionary")
        if self.strategy not in VALID_STRATEGIES:
            raise ValueError(
                f"Strategy must be one of {set(VALID_STRATEGIES)}, got '{self.strategy}'"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert hint to dictionary representation."""
        result = {
            "stability": self.stability,
            "priority": self.priority,
            "alternatives": self.alternatives.copy(),
            "strategy": self.strategy,
        }
        if self.metadata:
            result["metadata"] = self.metadata.copy()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SelectorHint":
        """Create hint from dictionary representation."""
        return cls(
            stability=data.get("stability", 0.5),
            priority=data.get("priority", 5),
            alternatives=data.get("alternatives", []),
            strategy=data.get("strategy", "linear"),
            metadata=data.get("metadata"),
        )


@dataclass
class HintSchema:
    """Schema for validating YAML hint fields.

    Provides validation and default values for hint fields in YAML configurations.
    """

    stability: float = 0.5
    priority: int = 5
    alternatives: List[str] = field(default_factory=list)
    strategy: str = "linear"
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def validate(cls, hint_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate and normalize hint data.

        Args:
            hint_data: Raw hint data from YAML

        Returns:
            Normalized hint data with defaults applied

        Raises:
            ValueError: If hint data is invalid
        """
        if not hint_data:
            default = cls()
            return {
                "stability": default.stability,
                "priority": default.priority,
                "alternatives": default.alternatives.copy(),
                "strategy": default.strategy,
                "metadata": default.metadata,
            }

        if not isinstance(hint_data, dict):
            raise ValueError("Hints must be a dictionary")

        validated = {}

        # Validate stability
        stability = hint_data.get("stability", cls().stability)
        if not isinstance(stability, (int, float)):
            raise ValueError("Stability must be a numeric value")
        if not (0.0 <= stability <= 1.0):
            raise ValueError("Stability must be between 0.0 and 1.0")
        validated["stability"] = stability

        # Validate priority
        priority = hint_data.get("priority", cls().priority)
        if not isinstance(priority, int):
            raise ValueError("Priority must be an integer")
        if priority < 1 or priority > 10:
            raise ValueError("Priority must be between 1 and 10")
        validated["priority"] = priority

        # Validate alternatives
        alternatives = hint_data.get("alternatives", cls().alternatives)
        if not isinstance(alternatives, list):
            raise ValueError("Alternatives must be a list")
        validated["alternatives"] = [str(alt) for alt in alternatives]

        # Validate strategy
        strategy = hint_data.get("strategy", cls().strategy)
        if strategy not in VALID_STRATEGIES:
            raise ValueError(
                f"Strategy must be one of {set(VALID_STRATEGIES)}, got '{strategy}'"
            )
        validated["strategy"] = strategy

        # Validate metadata
        metadata = hint_data.get("metadata")
        if metadata is not None and not isinstance(metadata, dict):
            raise ValueError("Metadata must be a dictionary")
        validated["metadata"] = metadata

        return validated

    def to_dict(self) -> Dict[str, Any]:
        """Convert schema to dictionary representation."""
        return {
            "stability": self.stability,
            "priority": self.priority,
            "alternatives": self.alternatives.copy(),
            "strategy": self.strategy,
            "metadata": self.metadata,
        }
