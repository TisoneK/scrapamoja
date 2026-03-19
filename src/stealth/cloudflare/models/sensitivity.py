"""Detection sensitivity level enum and mapping logic."""

from enum import IntEnum

from src.stealth.cloudflare.exceptions import (
    CloudflareConfigError,
    SensitivityConfigurationError,
)


class SensitivityLevel(IntEnum):
    """Detection sensitivity levels for challenge detection.

    Attributes:
        LOW: Conservative detection (1) - fewer false positives, may miss edge cases.
        MEDIUM: Balanced detection (3) - default recommendation.
        HIGH: Maximum detection (5) - more challenges detected, higher false positive risk.
    """

    LOW = 1
    MEDIUM = 3
    HIGH = 5


# String to SensitivityLevel mapping (case-insensitive)
_SENSITIVITY_STRING_MAP: dict[str, SensitivityLevel] = {
    "low": SensitivityLevel.LOW,
    "medium": SensitivityLevel.MEDIUM,
    "high": SensitivityLevel.HIGH,
}

# Valid string values for validation
VALID_SENSITIVITY_STRINGS: frozenset[str] = frozenset(_SENSITIVITY_STRING_MAP.keys())


def parse_sensitivity_value(value: int | str) -> int:
    """Parse a sensitivity value from either string or integer format.

    This function accepts sensitivity values in the following formats:
    - String: "high", "medium", "low" (case-insensitive)
    - Integer: 1, 2, 3, 4, 5

    Args:
        value: The sensitivity value as a string or integer.

    Returns:
        The numeric sensitivity value (1-5).

    Raises:
        SensitivityConfigurationError: If the value is invalid.

    Examples:
        >>> parse_sensitivity_value("high")
        5
        >>> parse_sensitivity_value("MEDIUM")
        3
        >>> parse_sensitivity_value(1)
        1
        >>> parse_sensitivity_value(5)
        5
    """
    if isinstance(value, str):
        normalized = value.lower().strip()
        if normalized in _SENSITIVITY_STRING_MAP:
            return _SENSITIVITY_STRING_MAP[normalized].value

        msg = f"Invalid sensitivity value: '{value}'. Must be one of: {', '.join(VALID_SENSITIVITY_STRINGS)} or 1-5"
        raise SensitivityConfigurationError(msg)

    if isinstance(value, int):
        if value < 1 or value > 5:
            msg = f"Invalid sensitivity value: {value}. Must be between 1 and 5"
            raise SensitivityConfigurationError(msg)
        return value

    # This should never be reached given the type annotation
    # but kept for safety
    raise SensitivityConfigurationError(
        f"Invalid sensitivity type: {type(value).__name__}. Must be str or int"
    )


def sensitivity_to_string(value: int) -> str:
    """Convert a numeric sensitivity value to its string representation.

    Args:
        value: The numeric sensitivity value (1-5).

    Returns:
        The string representation: "low", "medium", or "high".

    Raises:
        SensitivityConfigurationError: If the value is out of range.

    Examples:
        >>> sensitivity_to_string(1)
        'low'
        >>> sensitivity_to_string(3)
        'medium'
        >>> sensitivity_to_string(5)
        'high'
    """
    if value < 1 or value > 5:
        msg = f"Invalid sensitivity value: {value}. Must be between 1 and 5"
        raise SensitivityConfigurationError(msg)

    # Map numeric ranges to string values
    if value <= 2:
        return "low"
    if value == 3:
        return "medium"
    return "high"
