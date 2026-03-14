"""Exceptions for extraction mode routing."""

from src.sites.base.site_config import ExtractionMode


# Valid extraction modes for error messages
VALID_MODES = [mode.value for mode in ExtractionMode]


class ExtractionModeError(Exception):
    """Base exception for extraction mode errors."""
    pass


class InvalidExtractionModeError(ExtractionModeError):
    """Exception raised when an invalid extraction mode is specified.

    Attributes:
        mode: The invalid mode that was provided
        valid_modes: List of valid extraction modes
    """

    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.valid_modes = VALID_MODES
        message = (
            f"Invalid extraction mode: '{mode}'. "
            f"Valid modes are: {', '.join(sorted(VALID_MODES))}"
        )
        super().__init__(message)


class ExtractionModeNotSupportedError(ExtractionModeError):
    """Exception raised when an extraction mode is not yet implemented.

    Attributes:
        mode: The unsupported mode
        available_modes: List of available modes
    """

    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.available_modes = VALID_MODES
        message = (
            f"Extraction mode '{mode}' is not yet implemented. "
            f"Available modes: {', '.join(sorted(VALID_MODES))}"
        )
        super().__init__(message)


class ExtractionHandlerError(ExtractionModeError):
    """Exception raised when extraction handler fails."""
    pass
