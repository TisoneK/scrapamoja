"""Flag handling logic for Cloudflare configuration."""

from typing import Any, Optional, Union

from src.stealth.cloudflare.models.config import CloudflareConfig
from src.stealth.cloudflare.models.sensitivity import parse_sensitivity_value


def _parse_sensitivity(sensitivity: Union[int, str, None]) -> int:
    """Parse sensitivity value to integer.

    Args:
        sensitivity: Sensitivity value as int, str, or None.

    Returns:
        Numeric sensitivity value (1-5).
    """
    if sensitivity is None:
        return 3  # Default
    return parse_sensitivity_value(sensitivity)


def is_cloudflare_enabled(
    config: dict[str, Any] | CloudflareConfig | bool | None,
) -> bool:
    """Check if Cloudflare protection is enabled in the configuration.

    This function extracts the cloudflare_protected flag from various
    configuration formats and returns whether Cloudflare protection
    should be activated.

    Args:
        config: Configuration in one of these formats:
            - dict with cloudflare_protected key
            - dict with nested {"cloudflare": {"cloudflare_protected": True}} format
            - CloudflareConfig instance
            - CloudflareConfigSchema instance
            - None or empty

    Returns:
        True if cloudflare_protected is set to True, False otherwise.
    """
    if config is None:
        return False

    if isinstance(config, bool):
        return config

    if isinstance(config, CloudflareConfig):
        return config.is_enabled()

    if isinstance(config, dict):
        # Check top-level first
        if config.get("cloudflare_protected", False):
            return True
        # Also check nested {"cloudflare": {...}} format
        cloudflare_data = config.get("cloudflare")
        if isinstance(cloudflare_data, dict):
            return bool(cloudflare_data.get("cloudflare_protected", False))
        return False

    return False


def extract_cloudflare_config(
    config: dict[str, Any],
) -> Optional[CloudflareConfig]:
    """Extract Cloudflare configuration from a site config dictionary.

    Args:
        config: Site module configuration dictionary.

    Returns:
        CloudflareConfig instance if cloudflare_protected is True,
        None otherwise.
    """
    if not is_cloudflare_enabled(config):
        return None

    # Handle nested config format: {"cloudflare": {...}}
    cloudflare_data: dict[str, Any] = {}
    if "cloudflare" in config and isinstance(config["cloudflare"], dict):
        cloudflare_data = config["cloudflare"]

    # Determine if cloudflare_protected is True (check nested first, then top-level)
    is_enabled = cloudflare_data.get("cloudflare_protected", False)
    if not is_enabled:
        is_enabled = config.get("cloudflare_protected", False)
    if not is_enabled:
        return None

    # Get sensitivity value (string or int)
    sensitivity_input = cloudflare_data.get(
        "detection_sensitivity", config.get("detection_sensitivity")
    )

    return CloudflareConfig(
        cloudflare_protected=is_enabled,
        challenge_timeout=cloudflare_data.get(
            "challenge_timeout", config.get("challenge_timeout", 30)
        ),
        detection_sensitivity=_parse_sensitivity(sensitivity_input),
        auto_retry=cloudflare_data.get("auto_retry", config.get("auto_retry", True)),
    )


def merge_with_defaults(
    config: Optional[dict[str, Any]],
) -> CloudflareConfig:
    """Merge provided configuration with default values.

    Args:
        config: Optional configuration dictionary.

    Returns:
        CloudflareConfig with defaults applied.
    """
    if config is None:
        return CloudflareConfig()

    # Get sensitivity value (string or int)
    sensitivity_input = config.get("detection_sensitivity")

    return CloudflareConfig(
        cloudflare_protected=config.get("cloudflare_protected", False),
        challenge_timeout=config.get("challenge_timeout", 30),
        detection_sensitivity=_parse_sensitivity(sensitivity_input),
        auto_retry=config.get("auto_retry", True),
    )
