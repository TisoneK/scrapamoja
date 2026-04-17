"""
Strategy format converter for Flashscore selector configurations.

This module provides conversion between Flashscore's legacy strategy format
and the engine's StrategyPattern format, enabling seamless integration with
the adaptive selector engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Type, Union

if TYPE_CHECKING:
    from src.models.selector_models import StrategyPattern as EngineStrategyPattern
    from src.selectors.models import StrategyType


class LegacyStrategyType(str, Enum):
    """Legacy strategy types used in Flashscore YAML configs."""
    CSS = "css"
    XPATH = "xpath"
    TEXT = "text"
    ATTRIBUTE = "attribute"


class StrategyFormat(str, Enum):
    """Enumeration of supported strategy formats."""
    LEGACY = "legacy"  # Flashscore format: {type, selector, weight}
    STRATEGY_PATTERN = "strategypattern"  # Engine format: StrategyPattern


@dataclass
class LegacyStrategy:
    """Represents a strategy in Flashscore's legacy format."""
    type: str
    selector: str
    weight: float = 1.0
    alternatives: Optional[List[str]] = None
    confidence: Optional[float] = None


def convert_legacy_to_strategypattern(
    legacy_strategy: Union[LegacyStrategy, Dict[str, Any]],
    strategy_id: str,
    default_priority: int = 50
) -> "EngineStrategyPattern":
    """
    Convert a Flashscore legacy strategy to the engine's StrategyPattern format.

    Args:
        legacy_strategy: Either a LegacyStrategy dataclass or a dict with legacy format
        strategy_id: Unique identifier for the strategy
        default_priority: Default priority if weight conversion fails

    Returns:
        EngineStrategyPattern instance with converted values

    Conversion mapping:
        - type: Direct mapping (css → CSS, xpath → XPATH)
        - weight: Convert 0.0-1.0 to 1-100 (weight * 100)
        - selector: Move to config dict as 'selector' key
    """
    # Handle dict input
    if isinstance(legacy_strategy, dict):
        legacy_strategy = LegacyStrategy(
            type=legacy_strategy.get("type", "css"),
            selector=legacy_strategy.get("selector", ""),
            weight=legacy_strategy.get("weight", 1.0),
            alternatives=legacy_strategy.get("alternatives"),
            confidence=legacy_strategy.get("confidence")
        )

    # Convert type to StrategyType enum
    strategy_type = _convert_type(legacy_strategy.type)

    # Convert weight (0.0-1.0) to priority (1-100)
    priority = _convert_weight_to_priority(legacy_strategy.weight, default_priority)

    # Build config dict
    config: Dict[str, Any] = {"selector": legacy_strategy.selector}

    # Add alternatives if present
    if legacy_strategy.alternatives:
        config["alternatives"] = legacy_strategy.alternatives

    # Add confidence if present
    if legacy_strategy.confidence is not None:
        config["confidence"] = legacy_strategy.confidence

    # Create and return StrategyPattern
    # Use src.models.selector_models which has proper enum (inherits from str, Enum)
    from src.models.selector_models import StrategyPattern as EngineStrategyPattern

    return EngineStrategyPattern(
        id=strategy_id,
        type=strategy_type,
        priority=priority,
        config=config,
        success_rate=0.0,
        avg_resolution_time=0.0,
        is_active=True
    )


def _convert_type(legacy_type: str) -> Any:
    """
    Convert legacy type string to engine's StrategyType enum.

    Args:
        legacy_type: Type string from legacy format (e.g., "css", "xpath")

    Returns:
        StrategyType enum value or string representation
    """
    # Import from src.models.selector_models which has proper enum definition
    # This avoids the package vs module naming conflict in src/selectors/
    try:
        from src.models.selector_models import StrategyType
        
        # Map legacy types to StrategyType enum (only use values that exist)
        type_mapping = {
            "css": StrategyType.CSS,
            "xpath": StrategyType.XPATH,
            "text_anchor": StrategyType.TEXT_ANCHOR,
            "attribute_match": StrategyType.ATTRIBUTE_MATCH,
            "dom_relationship": StrategyType.DOM_RELATIONSHIP,
            "role_based": StrategyType.ROLE_BASED,
        }
        return type_mapping.get(legacy_type.lower(), StrategyType.CSS)
    except ImportError:
        # Fallback: return uppercase string
        return legacy_type.upper()


def _convert_weight_to_priority(weight: float, default: int = 50) -> int:
    """
    Convert weight (0.0-1.0) to priority (1-100).

    Args:
        weight: Weight value from legacy format (0.0 to 1.0)
        default: Default priority if conversion fails

    Returns:
        Priority value (1 to 100)
    """
    if weight is None:
        return default

    # Clamp weight to valid range
    weight = max(0.0, min(1.0, weight))

    # Convert to priority (1-100)
    priority = int(weight * 100)

    # Ensure minimum priority of 1
    return max(1, priority)


def detect_format(config: Dict[str, Any]) -> StrategyFormat:
    """
    Detect whether a config uses legacy or StrategyPattern format.

    Args:
        config: Selector configuration dict

    Returns:
        StrategyFormat enum indicating the detected format

    Detection rules:
        - Legacy format has "strategies" key with list of {type, selector, weight}
        - StrategyPattern format has "priority" in each strategy dict
    """
    # Check for StrategyPattern format first - if any strategy has 'priority', it's converted
    if "strategies" in config and isinstance(config.get("strategies"), list):
        first_strategy = config["strategies"][0] if config["strategies"] else {}
        if "priority" in first_strategy:
            return StrategyFormat.STRATEGY_PATTERN
        # Also check if 'type' is inside 'config' dict
        if "config" in first_strategy and isinstance(first_strategy.get("config"), dict):
            return StrategyFormat.STRATEGY_PATTERN

    # Check for legacy format indicators
    if "strategies" in config and isinstance(config.get("strategies"), list):
        first_strategy = config["strategies"][0] if config["strategies"] else {}
        if "type" in first_strategy and "selector" in first_strategy:
            return StrategyFormat.LEGACY

    # Check for StrategyPattern format indicators at root level
    if "type" in config and "priority" in config:
        return StrategyFormat.STRATEGY_PATTERN

    # Check for direct "config" key (StrategyPattern format)
    if "config" in config and isinstance(config.get("config"), dict):
        return StrategyFormat.STRATEGY_PATTERN

    # Default to legacy for backward compatibility
    return StrategyFormat.LEGACY


def convert_legacy_strategies(
    legacy_strategies: List[Dict[str, Any]],
    base_id: str = "strategy"
) -> List["EngineStrategyPattern"]:
    """
    Convert a list of legacy strategies to StrategyPattern format.

    Args:
        legacy_strategies: List of legacy strategy dicts
        base_id: Base identifier for strategies

    Returns:
        List of StrategyPattern instances
    """
    # Import here to avoid issues with runtime type checking
    # Use src.models.selector_models which has proper enum (inherits from str, Enum)
    try:
        from src.models.selector_models import StrategyPattern as EngineStrategyPattern
    except ImportError:
        raise ImportError("Cannot import StrategyPattern from src.models.selector_models")

    converted = []
    for idx, legacy in enumerate(legacy_strategies):
        strategy_id = f"{base_id}_{idx}" if base_id else f"strategy_{idx}"
        pattern = convert_legacy_to_strategypattern(legacy, strategy_id)
        converted.append(pattern)

    return converted


def convert_legacy_yaml(
    yaml_config: Dict[str, Any],
    selector_id: str = "selector"
) -> Dict[str, Any]:
    """
    Convert an entire Flashscore YAML config to use StrategyPattern format.

    This function handles the full conversion of a YAML configuration file,
    including strategies, metadata, and other fields.

    Args:
        yaml_config: Full YAML configuration dict
        selector_id: Identifier for the selector

    Returns:
        Converted configuration with StrategyPattern format
    """
    # Detect format first
    format_type = detect_format(yaml_config)

    # If already in StrategyPattern format, return as-is
    if format_type == StrategyFormat.STRATEGY_PATTERN:
        return yaml_config

    # Convert legacy format
    result = yaml_config.copy()

    if "strategies" in yaml_config:
        # Convert each strategy
        converted_strategies = convert_legacy_strategies(
            yaml_config["strategies"],
            base_id=selector_id
        )

        # Replace strategies with converted ones (as dicts for YAML serialization)
        result["strategies"] = [
            {
                "id": sp.id,
                "type": sp.type.value if hasattr(sp.type, 'value') else str(sp.type),
                "priority": sp.priority,
                "config": sp.config,
                "success_rate": sp.success_rate,
                "is_active": sp.is_active
            }
            for sp in converted_strategies
        ]

    return result


def is_legacy_format(file_path: str) -> bool:
    """
    Check if a YAML file uses legacy format based on its content.

    Args:
        file_path: Path to YAML file

    Returns:
        True if file uses legacy format, False otherwise
    """
    import yaml
    from pathlib import Path

    try:
        path = Path(file_path)
        if not path.exists():
            return False

        with open(path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        if config is None:
            return False

        return detect_format(config) == StrategyFormat.LEGACY

    except Exception:
        return False


# Backward compatibility alias
convert_flashscore_to_strategypattern = convert_legacy_to_strategypattern
