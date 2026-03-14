"""Interfaces and protocols for extraction mode routing.

This module defines the contracts for extraction mode handlers following
Pattern 1: Protocol-Based Interface from the architecture.
"""

from typing import Protocol, Any


class ExtractionHandlerProtocol(Protocol):
    """Protocol for extraction mode handlers.

    This defines the interface that all extraction mode handlers must implement.
    Each mode (raw, intercepted, hybrid, playwright) provides a handler
    that can perform data extraction.
    """

    async def extract(self, *args: Any, **kwargs: Any) -> Any:
        """Extract data using the configured mode.

        Args:
            *args: Mode-specific arguments
            **kwargs: Mode-specific keyword arguments

        Returns:
            Extracted data in mode-specific format
        """
        ...

    async def close(self) -> None:
        """Close and cleanup handler resources.

        This method must be called after extraction to properly release
        any resources (browser sessions, HTTP clients, etc.)
        """
        ...


class ExtractionModeProtocol(Protocol):
    """Protocol for extraction mode configuration.

    Defines the interface for objects that provide extraction mode configuration.
    """

    @property
    def extraction_mode(self) -> str:
        """Get the extraction mode string."""
        ...

    @property
    def site_name(self) -> str:
        """Get the site name."""
        ...

    @property
    def endpoint(self) -> str:
        """Get the endpoint URL."""
        ...
