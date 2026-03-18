"""YAML configuration loading for Cloudflare."""

from pathlib import Path
from typing import Any, Optional, Optional

import yaml

from src.stealth.cloudflare.config.flags import merge_with_defaults
from src.stealth.cloudflare.exceptions import (
    CloudflareConfigLoadError,
    CloudflareConfigNotFoundError,
)
from src.stealth.cloudflare.models.config import CloudflareConfig


class CloudflareConfigLoader:
    """Loader for Cloudflare configuration from YAML files.

    This class handles loading and validating Cloudflare configuration
    from site module YAML configuration files.
    """

    def __init__(self, config_path: Optional[Path] = None) -> None:
        """Initialize the configuration loader.

        Args:
            config_path: Optional path to the YAML configuration file.
        """
        self.config_path = config_path

    def load(self, config_path: Optional[Path] = None) -> CloudflareConfig:
        """Load Cloudflare configuration from a YAML file.

        Args:
            config_path: Path to the YAML configuration file.
                Uses instance config_path if not provided.

        Returns:
            CloudflareConfig instance with validated configuration.

        Raises:
            CloudflareConfigNotFoundError: If config file doesn't exist.
            CloudflareConfigLoadError: If config loading fails.
            CloudflareConfigValidationError: If config validation fails.
        """
        path = config_path or self.config_path
        if path is None:
            msg = "No configuration path provided"
            raise CloudflareConfigLoadError(msg)

        if not Path(path).exists():
            msg = f"Configuration file not found: {path}"
            raise CloudflareConfigNotFoundError(msg)

        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            msg = f"Failed to parse YAML: {e}"
            raise CloudflareConfigLoadError(msg) from e
        except OSError as e:
            msg = f"Failed to read config file: {e}"
            raise CloudflareConfigLoadError(msg) from e

        if not isinstance(data, dict):
            data = {}

        return self._parse_config(data)

    def load_from_dict(self, data: dict[str, Any]) -> CloudflareConfig:
        """Load Cloudflare configuration from a dictionary.

        Args:
            data: Configuration dictionary.

        Returns:
            CloudflareConfig instance with validated configuration.
        """
        return self._parse_config(data)

    def _parse_config(self, data: dict[str, Any]) -> CloudflareConfig:
        """Parse and validate configuration from dictionary.

        Args:
            data: Configuration dictionary.

        Returns:
            CloudflareConfig instance.

        Raises:
            CloudflareConfigValidationError: If validation fails.
        """
        cloudflare_data = data.get("cloudflare", {})

        if not cloudflare_data and not data.get("cloudflare_protected"):
            return CloudflareConfig()

        return CloudflareConfig(
            cloudflare_protected=cloudflare_data.get(
                "cloudflare_protected", data.get("cloudflare_protected", False)
            ),
            challenge_timeout=cloudflare_data.get(
                "challenge_timeout", data.get("challenge_timeout", 30)
            ),
            detection_sensitivity=cloudflare_data.get(
                "detection_sensitivity", data.get("detection_sensitivity", 3)
            ),
            auto_retry=cloudflare_data.get(
                "auto_retry", data.get("auto_retry", True)
            ),
        )

    @staticmethod
    def load_from_site_config(config: dict[str, Any] | None) -> CloudflareConfig:
        """Load Cloudflare config from a site module configuration.

        This is a convenience method that extracts Cloudflare settings
        from a complete site configuration dictionary.

        Args:
            config: Complete site module configuration. Can be None.

        Returns:
            CloudflareConfig instance.
        """
        if config is None:
            return CloudflareConfig()
        return merge_with_defaults(config)

    @staticmethod
    def is_cloudflare_site(config: dict[str, Any]) -> bool:
        """Check if a site configuration indicates Cloudflare protection.

        Args:
            config: Site module configuration dictionary.

        Returns:
            True if Cloudflare protection is enabled.
        """
        return (
            config.get("cloudflare_protected", False) == True
            or config.get("cloudflare", {}).get("cloudflare_protected", False) == True
        )
