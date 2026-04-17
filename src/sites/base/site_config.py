"""
Site configuration module for YAML-based site configuration.

This module provides Pydantic models and configuration loading for site-specific
YAML configuration files following Pattern 4: Config Model Structure.

Configuration files should be placed in: src/sites/{site_name}/config.yaml

Example config.yaml:
    endpoint: https://example.com/api
    auth_method: cookie
    extraction_mode: intercepted
"""

from enum import Enum
from pathlib import Path
from typing import Any, List, TYPE_CHECKING

import yaml
from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from src.network.direct_api.client import AsyncHttpClient


class AuthMethod(str, Enum):
    """Supported authentication methods."""
    NONE = "none"
    COOKIE = "cookie"
    BASIC = "basic"
    BEARER = "bearer"
    OAUTH2 = "oauth2"
    FORM = "form"


class ExtractionMode(str, Enum):
    """Supported extraction modes."""
    INTERCEPTED = "intercepted"
    PLAYWRIGHT = "playwright"
    HYBRID = "hybrid"
    RAW = "raw"


class InterceptedConfig(BaseModel):
    """Configuration for intercepted extraction mode.

    Attributes:
        url_patterns: List of regex patterns to match URLs for capture
        capture_body: Whether to capture response body (default True)
        capture_headers: Whether to capture response headers (default True)
    """

    url_patterns: list[str] = Field(
        default_factory=list,
        description="Regex patterns to match URLs for network interception",
    )
    capture_body: bool = Field(
        default=True,
        description="Whether to capture response body",
    )
    capture_headers: bool = Field(
        default=True,
        description="Whether to capture response headers",
    )

    model_config = {"str_strip_whitespace": True}


class SiteConfig(BaseModel):
    """
    Pydantic model for site configuration.

    This model validates the YAML configuration and provides type-safe
    access to site configuration values.
    """

    site_name: str = Field(
        default="",
        description="Name of the site"
    )
    endpoint: str = Field(
        description="Base URL endpoint for the site"
    )
    auth_method: AuthMethod = Field(
        default=AuthMethod.NONE,
        description="Authentication method to use"
    )
    extraction_mode: ExtractionMode = Field(
        default=ExtractionMode.RAW,
        description="Extraction mode to use (raw=Direct API, intercepted=Network capture, hybrid=Browser+HTTP, playwright=DOM)"
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Request timeout in seconds"
    )
    rate_limit: float | None = Field(
        default=None,
        ge=0,
        description="Rate limit in requests per second"
    )
    intercepted: InterceptedConfig | None = Field(
        default=None,
        description="Configuration for intercepted extraction mode"
    )

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, v: str) -> str:
        """Validate that endpoint is a valid URL."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Endpoint must start with http:// or https://")
        return v

    model_config = {
        "str_strip_whitespace": True,
        "use_enum_values": True,
    }

    def get_site_name(self) -> str:
        """Get the site name."""
        return ""

    def get_endpoint(self) -> str:
        """Get the site endpoint URL."""
        return self.endpoint

    def get_auth_method(self) -> str:
        """Get the authentication method."""
        return self.auth_method

    def get_extraction_mode(self) -> str:
        """Get the extraction mode."""
        return self.extraction_mode

    def get_timeout(self) -> int:
        """Get the request timeout in seconds."""
        return self.timeout

    def get_rate_limit(self) -> float | None:
        """Get the rate limit in requests per second."""
        return self.rate_limit

    def get_intercepted_config(self) -> InterceptedConfig | None:
        """Get the intercepted mode configuration."""
        return self.intercepted


class SiteConfigLoader:
    """
    Loader for site-specific YAML configuration files.

    This class handles loading and validation of site configuration
    from YAML files following the Pattern 4: Config Model Structure.
    """

    def __init__(self, site_name: str):
        """
        Initialize the loader for a specific site.

        Args:
            site_name: Name of the site module (e.g., 'flashscore', 'wikipedia')
        """
        self.site_name = site_name
        self._config: SiteConfig | None = None

    @property
    def config_path(self) -> Path:
        """Get the path to the site's config.yaml file."""
        return Path(__file__).parent.parent / self.site_name / "config.yaml"

    def load(self, force_reload: bool = False) -> SiteConfig:
        """
        Load and validate site configuration from YAML file.

        Args:
            force_reload: Force reload even if config is cached

        Returns:
            Validated SiteConfig instance

        Raises:
            FileNotFoundError: If config.yaml doesn't exist
            ValueError: If configuration is invalid
        """
        if self._config is not None and not force_reload:
            return self._config

        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Site configuration file not found: {self.config_path}"
            )

        with open(self.config_path, encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        if config_data is None:
            raise ValueError(f"Empty configuration file: {self.config_path}")

        self._config = SiteConfig(**config_data)
        return self._config

    def load_or_none(self) -> SiteConfig | None:
        """
        Load configuration, returning None if not found or invalid.

        Returns:
            SiteConfig if loaded successfully, None otherwise
        """
        try:
            return self.load()
        except (FileNotFoundError, ValueError, yaml.YAMLError):
            return None

    @classmethod
    def from_site(cls, site_name: str) -> "SiteConfigLoader":
        """
        Factory method to create a loader for a site.

        Args:
            site_name: Name of the site module

        Returns:
            SiteConfigLoader instance
        """
        return cls(site_name)

    def get_config_dict(self) -> dict[str, Any]:
        """
        Get configuration as a dictionary.

        Returns:
            Configuration dictionary
        """
        config = self.load()
        return {
            "endpoint": config.endpoint,
            "auth_method": config.auth_method,
            "extraction_mode": config.extraction_mode,
            "timeout": config.timeout,
            "rate_limit": config.rate_limit,
        }


def load_site_config(site_name: str) -> SiteConfig:
    """
    Convenience function to load site configuration.

    Args:
        site_name: Name of the site module

    Returns:
        Validated SiteConfig instance
    """
    loader = SiteConfigLoader(site_name)
    return loader.load()


def load_site_config_or_none(site_name: str) -> SiteConfig | None:
    """
    Convenience function to load site configuration, returning None if not found.

    Args:
        site_name: Name of the site module

    Returns:
        SiteConfig if found and valid, None otherwise
    """
    loader = SiteConfigLoader(site_name)
    return loader.load_or_none()


def create_http_client_from_config(
    config: SiteConfig,
    site_name: str,
    rate_capacity: float = 10.0
) -> "AsyncHttpClient":
    """
    Create an AsyncHttpClient from SiteConfig.

    This factory function creates a configured HTTP client using values
    from the site configuration (endpoint, timeout, rate_limit).

    Args:
        config: The site configuration
        site_name: Name of the site (used for logging/identification)
        rate_capacity: Default maximum tokens per domain (default: 10)

    Returns:
        Configured AsyncHttpClient instance

    Example:
        config = load_site_config("wikipedia")
        async with create_http_client_from_config(config, "wikipedia") as client:
            response = await client.get("/api/search").execute()
    """
    from src.network.direct_api.client import AsyncHttpClient

    rate_limit = config.rate_limit if config.rate_limit else 10.0

    return AsyncHttpClient(
        base_url=config.endpoint,
        rate_limit=rate_limit,
        rate_capacity=rate_capacity
    )
