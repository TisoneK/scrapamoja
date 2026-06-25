"""Site configuration interfaces for dependency injection.

This module defines abstract interfaces for site configuration following
Pattern 4: Config Model Structure. These interfaces allow for dependency
injection of site configuration into transport and other layers.

Usage:
    from src.sites.base.interfaces import SiteConfigProvider, get_site_config

    class MyClient:
        def __init__(self, config_provider: SiteConfigProvider):
            self.config = config_provider.get_config()
"""

from abc import ABC, abstractmethod
from typing import Any


class SiteConfigProvider(ABC):
    """Abstract interface for providing site configuration.

    This interface allows for dependency injection of site configuration
    into components that need access to site settings (endpoint, auth, etc.).
    """

    @abstractmethod
    def get_site_name(self) -> str:
        """Get the site name."""
        pass

    @abstractmethod
    def get_endpoint(self) -> str:
        """Get the site endpoint URL."""
        pass

    @abstractmethod
    def get_auth_method(self) -> str:
        """Get the authentication method."""
        pass

    @abstractmethod
    def get_extraction_mode(self) -> str:
        """Get the extraction mode."""
        pass

    @abstractmethod
    def get_timeout(self) -> int:
        """Get the request timeout in seconds."""
        pass

    @abstractmethod
    def get_rate_limit(self) -> float | None:
        """Get the rate limit in requests per second."""
        pass

    @abstractmethod
    def get_config_dict(self) -> dict[str, Any]:
        """Get the full configuration as a dictionary."""
        pass


class TransportFactory(ABC):
    """Abstract interface for creating transport clients from site configuration.

    This interface allows for creating HTTP clients or other transport
    mechanisms that are configured based on site settings.
    """

    @abstractmethod
    def create_client(self, config: SiteConfigProvider) -> Any:
        """Create a transport client from site configuration.

        Args:
            config: The site configuration provider

        Returns:
            A configured transport client
        """
        pass
