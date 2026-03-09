"""
Hint parsing logic for YAML selector configurations.

This module provides functionality for parsing and validating hint fields
from YAML selector configurations.
"""

from typing import Dict, Any, Optional
import logging

from src.selectors.exceptions import SelectorConfigurationError
from .models import SelectorHint, HintSchema

logger = logging.getLogger(__name__)


def parse_hints(hint_data: Optional[Dict[str, Any]]) -> SelectorHint:
    """Parse and validate hint data from YAML configuration.

    Args:
        hint_data: Raw hint data from YAML selector

    Returns:
        Parsed and validated SelectorHint object

    Raises:
        SelectorConfigurationError: If hint data is invalid
    """
    if not hint_data:
        logger.debug("No hint data provided, using defaults")
        return SelectorHint()

    try:
        logger.debug("Parsing hint data: %s", hint_data)
        validated_data = HintSchema.validate(hint_data)
        hint = SelectorHint.from_dict(validated_data)
        logger.debug("Successfully parsed hints: %s", hint.to_dict())
        return hint
    except ValueError as e:
        raise SelectorConfigurationError(
            message=f"Invalid hint configuration: {str(e)}",
            selector_id=None
        ) from e
